from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


model_name = "google/flan-t5-base"

tokenizer = AutoTokenizer.from_pretrained(model_name)

model = AutoModelForSeq2SeqLM.from_pretrained(model_name)


def summarize_document(text):

    prompt = f"Summarize this document:\n{text}"

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        max_length=512,
        truncation=True
    )

    outputs = model.generate(
        **inputs,
        max_new_tokens=150
    )

    summary = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True
    )

    return summary