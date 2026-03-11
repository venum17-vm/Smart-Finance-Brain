from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_name = "microsoft/Phi-3-mini-4k-instruct"

tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    trust_remote_code=True
)

# Load with 4-bit quantization (saves memory)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
    load_in_4bit=True,  # 4-bit quantization
    bnb_4bit_compute_dtype=torch.float16
)


def summarize_document(text, max_length=200):
    """
    Summarize document using Phi-3 Mini (optimized)
    """
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that creates concise summaries."
        },
        {
            "role": "user",
            "content": f"Summarize this document:\n\n{text}"
        }
    ]
    
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        max_length=3072,
        truncation=True
    ).to(model.device)
    
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_length,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    
    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract assistant response
    if "<|assistant|>" in full_output:
        summary = full_output.split("<|assistant|>")[-1].strip()
    else:
        summary = full_output.split(text)[-1].strip()
    
    return summary