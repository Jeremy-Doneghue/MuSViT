"""Bounded in-sample overfit experiment using the existing MuSViT decoder.

The encoder is frozen; raw image features are cached without targets. All greedy
predictions start from BOS alone, with no grammar mask or teacher-forced prefix.
"""

import argparse
from datetime import datetime, timezone
import json
from math import isqrt
from pathlib import Path
import random
import resource
import sys
import time

import editdistance
from safetensors.torch import load_file
import torch
from torch import nn
import torch.nn.functional as F
from transformers import ViTConfig, ViTModel

from .pilot_data import PilotDataset, export_pilot, sha256
from .score_codec import CodecError, PROFILE, VOCABULARY, VOCABULARY_SHA256, W2I, decode
from .score_semantics import inspect_score
from .smt_foundation.configuration_smt import SMTFoundationConfig
from .smt_foundation.modeling_smt import SMTFoundationModelForCausalLM


def local_encoder(weights, config_path):
    source = json.loads(Path(config_path).read_text())
    fields = ("hidden_size", "num_hidden_layers", "num_attention_heads", "intermediate_size", "image_size",
              "patch_size", "num_channels", "qkv_bias", "layer_norm_eps", "hidden_act",
              "hidden_dropout_prob", "attention_probs_dropout_prob")
    config = ViTConfig(**{key: source[key] for key in fields if key in source})
    encoder = ViTModel(config, add_pooling_layer=False)
    weights = load_file(str(weights), device="cpu")
    state = {key.removeprefix("vit."): value for key, value in weights.items() if key.startswith("vit.")}
    if not state:
        raise ValueError("expected local MuSViT/MAE vit.* encoder weights")
    encoder.load_state_dict(state, strict=True)
    return encoder


def make_model(encoder, resolution, maxlen, width=128, layers=2):
    config = SMTFoundationConfig(foundation_architecture="ViTMAEBase", foundation_weights="local-explicit",
                                 maxh=resolution, maxw=resolution, maxlen=maxlen,
                                 out_categories=len(VOCABULARY), padding_token=0, in_channels=3,
                                 w2i=W2I, i2w=dict(enumerate(VOCABULARY)),
                                 d_model=width, dim_ff=width * 2, num_dec_layers=layers)
    model = SMTFoundationModelForCausalLM(config, encoder=encoder)
    for module in model.decoder.modules():
        if isinstance(module, nn.Dropout):
            module.p = 0.0
    return model


class CachedGreedy:
    """Incremental eval of the existing decoder, with per-layer projected K/V.

    Tested against full-prefix logits. Matches this implementation's unscaled
    attention arithmetic; it does not replace training attention or mask tokens.
    """

    def __init__(self, model, encoder_output):
        if model.training:
            raise ValueError("cached generation requires model.eval()")
        self.model = model
        patches = model.adaptor(encoder_output[:, :, 1:])
        side = isqrt(patches.shape[-1])
        spatial = patches.reshape(1, model.config.d_model, side, side)
        raw = patches.permute(2, 0, 1)
        enhanced = model.positional_2D(spatial).flatten(2).permute(2, 0, 1)
        self.cross = [(self.project(layer.cross_attention.lk(enhanced)),
                       self.project(layer.cross_attention.lv(raw))) for layer in model.decoder.decoder.layers]
        self.cache = [None] * len(self.cross)

    @staticmethod
    def project(x):
        # The existing decoder always uses four heads and batch size one here.
        return x.reshape(x.shape[0], 4, x.shape[-1] // 4).transpose(0, 1)

    def attention(self, module, query, keys, values):
        q = self.project(module.lq(query))
        attention = torch.softmax(torch.bmm(q, keys.transpose(1, 2)), dim=-1)
        result = torch.bmm(attention, values).transpose(0, 1).contiguous().reshape(1, 1, -1)
        return module.out_proj(result)

    def step(self, token, position):
        decoder = self.model.decoder
        token = torch.tensor([[token]], device=decoder.embedding.weight.device)
        x = decoder.embedding(token).permute(0, 2, 1)
        x = decoder.positional_1D(x, start=position).permute(2, 0, 1)
        for index, layer in enumerate(decoder.decoder.layers):
            module = layer.input_attention
            keys, values = self.project(module.lk(x)), self.project(module.lv(x))
            if self.cache[index] is not None:
                old_keys, old_values = self.cache[index]
                keys, values = torch.cat((old_keys, keys), 1), torch.cat((old_values, values), 1)
            self.cache[index] = keys, values
            x = layer.norm1(x + self.attention(module, x, keys, values))
            keys, values = self.cross[index]
            x = layer.norm2(x + self.attention(layer.cross_attention, x, keys, values))
            x = layer.norm3(x + layer.ffNet(x))
        return decoder.out_layer(decoder.end_relu(x).permute(1, 2, 0))[0, :, 0]


@torch.inference_mode()
def greedy(model, features, maxlen):
    cache = CachedGreedy(model, features)
    tokens = [W2I["<bos>"]]
    for position in range(maxlen - 1):
        next_token = int(cache.step(tokens[-1], position).argmax().item())
        tokens.append(next_token)
        if next_token == W2I["<eos>"]:
            break
    return tokens


@torch.inference_mode()
def evaluate(model, features, targets, records, output, step, swapped=False):
    model.eval()
    folder = output / (f"eval_{step:05d}" + ("_swapped" if swapped else ""))
    folder.mkdir(exist_ok=False)
    results = []
    started = time.perf_counter()
    for index, (target, record) in enumerate(zip(targets, records)):
        feature_index = (index + 1) % len(features) if swapped else index
        prediction = greedy(model, features[feature_index], model.maxlen)
        valid, semantic_equal, error = False, False, None
        name = record["name"]
        try:
            xml = decode(prediction)
            valid = True
            (folder / f"{name}.musicxml").write_text(xml)
            semantic_equal = inspect_score(xml) == inspect_score(decode(target))
        except (CodecError, ValueError) as exc:
            error = str(exc)
        predicted = dict(tokens=prediction, profile=PROFILE, vocabulary_sha256=VOCABULARY_SHA256,
                         target_name=name, image_name=records[feature_index]["name"], error=error)
        (folder / f"{name}.json").write_text(json.dumps(predicted, indent=2))
        results.append(dict(name=name, image_name=records[feature_index]["name"],
                            exact=prediction == target, valid_score=valid, semantic_equal=semantic_equal,
                            token_error=editdistance.eval(prediction, target) / len(target),
                            predicted_length=len(prediction), target_length=len(target),
                            eos=prediction[-1] == W2I["<eos>"], truncated=prediction[-1] != W2I["<eos>"],
                            error=error))
    summary = dict(step=step, swapped=swapped, exact=sum(x["exact"] for x in results),
                   valid=sum(x["valid_score"] for x in results), semantic_equal=sum(x["semantic_equal"] for x in results),
                   count=len(results), seconds=time.perf_counter() - started, examples=results)
    (folder / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "examples"}), flush=True)
    return summary


def train(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    device = torch.device(args.device)
    if device.type == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS unavailable in this execution context; run with GPU access or explicitly select cpu")
    data = PilotDataset(args.dataset, args.resolution, args.limit)
    targets = [ids.tolist() for _, ids in data.samples]
    maxlen = max(map(len, targets)) + 32
    encoder = local_encoder(args.encoder_weights, args.encoder_config)
    model = make_model(encoder, args.resolution, maxlen, args.width, args.layers).to(device)
    if args.start_from:
        checkpoint = torch.load(args.start_from, map_location="cpu", weights_only=True)
        if checkpoint["vocabulary_sha256"] != VOCABULARY_SHA256:
            raise ValueError("checkpoint vocabulary mismatch")
        result = model.load_state_dict(checkpoint["trainable_state"], strict=False)
        if result.unexpected_keys or any(not k.startswith("encoder.") for k in result.missing_keys):
            raise ValueError("incompatible warm-start checkpoint")
    config = vars(args).copy()
    config.update(profile=PROFILE, vocabulary_sha256=VOCABULARY_SHA256, maxlen=maxlen,
                  encoder_weights_sha256=sha256(args.encoder_weights), encoder_config=json.loads(Path(args.encoder_config).read_text()),
                  dataset_manifest_sha256=sha256(Path(args.dataset) / "manifest.json"),
                  implementation_sha256={p.name: sha256(p) for p in (Path(__file__), Path(__file__).with_name("pilot_data.py"),
                                            Path(__file__).parent / "smt_foundation/modeling_smt.py")},
                  trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
                  frozen_encoder_parameters=sum(p.numel() for p in model.encoder.parameters()),
                  torch=torch.__version__, started_utc=datetime.now(timezone.utc).isoformat(),
                  augmentation=False, token_corruption=False, decoder_dropout=0, batch_size=1,
                  raw_encoder_feature_cache=True, image_normalization="RGB [0,1], bilinear square resize",
                  target_lengths=[len(t) for t in targets], warm_start_sha256=sha256(args.start_from) if args.start_from else None)
    (output / "config.json").write_text(json.dumps(config, indent=2))
    model.eval()
    features = []
    start = time.perf_counter()
    with torch.inference_mode():
        for index, (image, _) in enumerate(data.samples):
            # clone outside inference mode below makes features usable as saved
            # tensors in the trainable adaptor's backward pass.
            features.append(model.forward_encoder(image.to(device)).permute(0, 2, 1).contiguous())
            print(json.dumps(dict(cached_image=data.records[index]["name"], elapsed=time.perf_counter() - start)), flush=True)
    features = [feature.clone() for feature in features]
    caching_seconds = time.perf_counter() - start
    # Confirm incremental cache matches the real full-prefix decoder before use.
    with torch.inference_mode():
        cache = CachedGreedy(model, features[0])
        prefix = targets[0][:12]
        for pos, token in enumerate(prefix):
            incremental = cache.step(token, pos)
            if pos in (0, len(prefix) - 1):
                full = model.forward_decoder(features[0], torch.tensor([prefix[:pos + 1]], device=device)).logits[0, :, -1]
                torch.testing.assert_close(incremental, full, atol=2e-4, rtol=2e-4)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0)
    initial = evaluate(model, features, targets, data.records, output, 0)
    history = output / "training.jsonl"
    order, losses, last = [], [], initial
    started = time.perf_counter()
    for step in range(1, args.steps + 1):
        if not order:
            order = list(range(len(data)))
            random.shuffle(order)
        index = order.pop()
        _, inputs, labels = data[index]
        model.train()
        model.encoder.eval()
        optimizer.zero_grad(set_to_none=True)
        logits = model.forward_decoder(features[index], inputs.to(device)).logits
        loss = F.cross_entropy(logits, labels.to(device))
        if not torch.isfinite(loss):
            raise RuntimeError("nonfinite training loss")
        loss.backward()
        nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
        optimizer.step()
        losses.append(float(loss.item()))
        if step % 25 == 0 or step == 1:
            metric = dict(step=step, loss=losses[-1], mean_recent_loss=sum(losses[-25:]) / len(losses[-25:]),
                          elapsed_seconds=time.perf_counter() - started)
            with history.open("a") as stream:
                stream.write(json.dumps(metric) + "\n")
            print(json.dumps(metric), flush=True)
        if step % args.eval_every == 0 or step == args.steps:
            last = evaluate(model, features, targets, data.records, output, step)
            state = {key: value.detach().cpu() for key, value in model.state_dict().items() if not key.startswith("encoder.")}
            torch.save(dict(trainable_state=state, vocabulary_sha256=VOCABULARY_SHA256, profile=PROFILE,
                            step=step, width=args.width, layers=args.layers), output / "last.pt")
            if last["exact"] == len(data):
                break
    swapped = evaluate(model, features, targets, data.records, output, step, swapped=True) if len(data) > 1 else None
    peak_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    final = dict(success=last["exact"] == len(data), steps=step, initial=initial, final=last, swapped=swapped,
                 training_seconds=time.perf_counter() - started, caching_seconds=caching_seconds,
                 first_loss=losses[0], last_loss=losses[-1], peak_process_rss_bytes=peak_bytes,
                 mps_driver_allocated_bytes=torch.mps.driver_allocated_memory() if device.type == "mps" else None,
                 encoder_frozen=all(not p.requires_grad and p.grad is None for p in model.encoder.parameters()),
                 limitation="in-sample clean-score memorization; not generalization or degraded-scan evaluation")
    (output / "result.json").write_text(json.dumps(final, indent=2))
    print(json.dumps({k: v for k, v in final.items() if k not in ("initial", "final", "swapped")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--output", required=True)
    run = sub.add_parser("train")
    run.add_argument("--dataset", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--encoder-weights", required=True)
    run.add_argument("--encoder-config", required=True)
    run.add_argument("--device", choices=("cpu", "mps", "cuda"), default="cpu")
    run.add_argument("--resolution", type=int, default=1024)
    run.add_argument("--limit", type=int, default=1)
    run.add_argument("--width", type=int, default=128)
    run.add_argument("--layers", type=int, default=2)
    run.add_argument("--steps", type=int, default=1500)
    run.add_argument("--eval-every", type=int, default=100)
    run.add_argument("--lr", type=float, default=0.001)
    run.add_argument("--seed", type=int, default=7)
    run.add_argument("--threads", type=int, default=4)
    run.add_argument("--start-from")
    args = parser.parse_args()
    if args.command == "export":
        manifest = export_pilot(args.output)
        print(json.dumps(dict(examples=len(manifest["records"]), lengths=[r["target_length"] for r in manifest["records"]])))
    else:
        if min(args.steps, args.eval_every, args.limit, args.threads, args.layers) < 1 or args.width % 4 or args.width < 4:
            parser.error("positive run limits and a decoder width divisible by four are required")
        if args.resolution < 16 or args.resolution % 16:
            parser.error("resolution must be a positive multiple of 16")
        train(args)


if __name__ == "__main__":
    main()
