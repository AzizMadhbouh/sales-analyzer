import json

import torch
from torch import nn
from transformers import ModernBertConfig, ModernBertModel, PreTrainedModel
from transformers.modeling_outputs import ModelOutput

TASKS = ("category", "component")


class ModernBERTMultiTask(PreTrainedModel):
    config_class = ModernBertConfig
    base_model_prefix = "modernbert"
    main_input_name = "input_ids"
    supports_gradient_checkpointing = True
    _supports_sdpa = True
    _supports_flash_attn = False

    def __init__(self, config, num_labels=None):
        config._attn_implementation = "eager"
        config._supports_sdpa = True
        super().__init__(config)
        if num_labels is None:
            num_labels = getattr(config, "multitask_num_labels", {})
        self.num_labels = num_labels
        self._weight_buffers = {}
        for task in TASKS:
            w = (getattr(config, "task_class_weights", None) or {}).get(task)
            if w is not None:
                buf = torch.tensor(w, dtype=torch.float32)
                self._weight_buffers[task] = buf
                self.register_buffer(f"task_weights_{task}", buf)
        self.modernbert = ModernBertModel(config)
        self.heads = nn.ModuleDict(
            {task: nn.Linear(config.hidden_size, num_labels[task]) for task in TASKS}
        )
        self.post_init()

    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        kwargs.setdefault("torch_dtype", torch.float32)
        kwargs.setdefault("trust_remote_code", True)
        if "attn_implementation" not in kwargs:
            kwargs["attn_implementation"] = "eager"
        model = super().from_pretrained(*args, **kwargs)
        for name, buf in model.named_buffers():
            if buf.is_meta:
                setattr(model, name, torch.empty(buf.shape, dtype=buf.dtype))
        model._weight_buffers = {
            t: getattr(model, f"task_weights_{t}")
            for t in TASKS if hasattr(model, f"task_weights_{t}")
        }
        return model

    def forward(self, input_ids=None, attention_mask=None, labels=None, return_dict=None, **kwargs):
        outputs = self.modernbert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            return_dict=True,
        )
        pooled = outputs.last_hidden_state[:, 0]
        logits = {task: self.heads[task](pooled) for task in TASKS}
        loss = None
        if labels is not None:
            losses = []
            for task in TASKS:
                w = self._weight_buffers.get(task)
                losses.append(
                    nn.functional.cross_entropy(
                        logits[task], labels[task].long().view(-1),
                        weight=None if w is None else w.to(logits[task].device),
                    )
                )
            loss = torch.stack(losses).mean()
        return ModelOutput(loss=loss, logits=logits)


def set_task_weights(model, task, weights):
    buf = torch.tensor(weights, dtype=torch.float32)
    model.register_buffer(f"task_weights_{task}", buf)
    model._weight_buffers[task] = buf


def save_with_maps(model, tokenizer, output_dir, label_maps):
    model.config.multitask_num_labels = model.num_labels
    tw = {t: w.tolist() for t, w in model._weight_buffers.items()}
    if tw:
        model.config.task_class_weights = tw
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    with open(output_dir + "/label_maps.json", "w", encoding="utf-8") as f:
        json.dump(label_maps, f, indent=2)