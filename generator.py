import base64

import replicate


def load_prompt(template_path, **kwargs):
    with open(template_path, "r") as file:
        template = file.read()
        # format of args is **{name}**
    return template.format(**kwargs)


def analyze_image(image_data_uri, image_prompt):
    output = replicate.run(
        "anthropic/claude-4.5-sonnet",
        input={
            "image": image_data_uri,
            "prompt": image_prompt
        }
    )
    return "".join(output) if isinstance(output, list) else str(output)

def generate_insights_from_image(image_file, user_prompt) -> str:
    img_bytes = image_file.getvalue()
    base64_img = base64.b64encode(img_bytes).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{base64_img}"

    #pass args name if **{name}** then name=""
    input_prompt = load_prompt(
        "image_to_text_prompt.txt",
        campaign_context=user_prompt
    )

    return analyze_image(data_uri, input_prompt)