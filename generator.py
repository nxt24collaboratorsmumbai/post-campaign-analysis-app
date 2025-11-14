import base64
import tempfile
from pathlib import Path
import replicate
from crewai import Crew, Task, Agent, LLM
# from data_utils import(load_uploaded_files, build_llm_inputs
from data_utils_new import (build_schema_summary, load_multiple_tables, build_numeric_summary,
                            build_categorical_summary, build_sample_rows, build_kpi_mapping_summary, build_kpi_view,
                            build_file_overview, generate_charts_from_spec)
from crew_setup import(build_crew)


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



def encode_image_to_data_uri(image_file):
    img_bytes = image_file.getvalue()
    base64_img = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{base64_img}"

# ---------- CrewAI Implementation ----------
def generate_insights_from_image_1(image_file, user_prompt):
    # Step 1: Prepare input
    data_uri = encode_image_to_data_uri(image_file)
    formatted_prompt = load_prompt(
        "image_to_text_prompt.txt",
        campaign_context=user_prompt
    )

    # Step 2: Define the Agent
    image_analyst = Agent(
        role="Image Insights Analyst",
        goal="Extract meaningful insights, patterns, and KPIs from dashboard or campaign images.",
        backstory=(
            "An expert data analyst skilled at reading BI dashboards, "
            "charts, and campaign visuals to extract detailed insights."
        ),
        llm="gpt-4o"  # or "gpt-4o", "claude-3.5-sonnet", etc.
    )

    # Step 3: Define the Task for this agent
    task = Task(
        description=f"""
        Analyze the following image data and user prompt, then generate concise, structured insights.

        Image (base64 URI):
        {data_uri}

        Context:
        {formatted_prompt}
        """,
        agent=image_analyst,
        expected_output="A detailed, structured text summary of insights from the image."
    )

    # Step 4: (Optional) Define a Crew to manage execution
    crew = Crew(
        agents=[image_analyst],
        tasks=[task]
    )

    # Step 5: Run the Crew and get result
    result = crew.kickoff()
    return "".join(result.raw)



def generate_json_to_ppt():
    llm = LLM(
        model="gpt-4o-mini",  # or whichever model you want
        temperature=0.0,
        max_tokens=2000
    )
    json_to_ppt = Agent(
        name="json_to_ppt",
        role=(
            "You are Agent 3 — Insights→JSON Converter: you receive structured "
            "and unstructured insights from Agent 1 and Agent 2 and the user. "
            "Your job is to validate and normalize inputs, resolve conflicts, "
            "and emit a schema-validated JSON payload for the PPT builder."
        ),
        goal=(
            "Produce a slides[] JSON (fixed schema) that includes title, layout, "
            "content blocks, speaker_notes, visuals (type, data_ref, image_ref), "
            "provenance, and confidence scores for a 13-page post-campaign deck."
        ),
        backstory=(
            "You are a campaign-focused research analyst used to noisy analytics "
            "data and human notes; favor numeric sources for KPIs, provide clear "
            "assumptions, and always emit a provenance field."
        ),
        llm=llm,  # ensure llm is instantiated before this
        verbose=True,
        allow_delegation=False,
    )

    task_insights_to_json = Task(
        description=(
            "Receive insights, metrics, narratives, and image references from Agent 1, "
            "Agent 2, and the user. Validate, clean, harmonize, and convert them into a "
            "structured JSON format suitable for automatic PowerPoint generation. "
            "The final output should represent a 13-slide post-campaign analysis deck."
        ),
        expected_output=(
            "A single JSON object containing exactly 13 slides. Each slide must include: "
            "slide_number, title, key_points, narrative, speaker_notes, visuals "
            "(e.g., charts, images), data_references, and provenance. The JSON must be "
            "well-structured, schema-consistent, and ready to be passed to the PPT builder."
        ),
        agent=json_to_ppt
    )

    crew = Crew(
        agents=[json_to_ppt],
        tasks=[task_insights_to_json],
        verbose=True
    )

def expand_input_paths(raw_inputs):
    """
    Expand provided paths into a list of actual CSV/XLS/XLSX file paths.
    """
    files = []
    for item in raw_inputs:
        p = Path(item)
        if p.is_dir():
            files.extend(sorted(p.glob("*.csv")))
            files.extend(sorted(p.glob("*.xlsx")))
            files.extend(sorted(p.glob("*.xls")))
        else:
            files.append(p)

    unique_files = []
    seen = set()
    for f in files:
        if not f.exists():
            raise FileNotFoundError(f"Input path does not exist: {f}")
        fp = f.resolve()
        if fp not in seen:
            seen.add(fp)
            unique_files.append(str(fp))

    if not unique_files:
        raise ValueError("No valid CSV/XLS/XLSX files found in the provided inputs.")

    return unique_files

def generate_insights_from_data_file(upload_data_file, prompt):
    out_dir = Path("output")  # or any folder name you prefer
    charts_dir = out_dir / "charts"
    reports_dir = out_dir / "reports"

    charts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    # df, summaries = load_uploaded_files([upload_data_file])
    # llm_inputs = build_llm_inputs(df, summaries)
    # file_paths = upload_data_file
    # print("Using the following input files:")
    # for f in file_paths:
    #     print(f"  - {f}")

    if upload_data_file:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload_data_file.name).suffix) as tmp:
            tmp.write(upload_data_file.read())
            temp_path = tmp.name

    # ------------------------------
    # Step 2: Load + combine
    # ------------------------------
    print("Loading and combining tables...")
    combined_df, file_summaries = load_multiple_tables(
        [temp_path],
        max_rows_for_llm=500,
    )

    file_overview = build_file_overview(file_summaries)

    # ------------------------------
    # Step 3: Extract KPI-only view
    # ------------------------------
    print("Building KPI-only view (lands, cost, HVEA, channel)...")
    kpi_df, kpi_mapping = build_kpi_view(combined_df)
    kpi_mapping_str = build_kpi_mapping_summary(kpi_mapping)

    # ------------------------------
    # Step 4: KPI summaries given to AI
    # ------------------------------
    print("Building KPI summaries for agents...")
    schema_summary = build_schema_summary(kpi_df)
    numeric_summary = build_numeric_summary(kpi_df)
    categorical_summary = build_categorical_summary(kpi_df)
    sample_rows = build_sample_rows(kpi_df, n=5)

    # ------------------------------
    # Step 5: Build the crew
    # ------------------------------
    print("Building crew and executing agentic flow...")
    crew = build_crew(model="gpt-4o")

    # First execution (Campaign Manager + Data Analyst)
    inputs = {
        "file_overview": file_overview,
        "kpi_mapping": kpi_mapping_str,
        "schema_summary": schema_summary,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "sample_rows": sample_rows,
        "chart_paths": "",
    }


    result = crew.kickoff(inputs=inputs)

    # ------------------------------
    # Step 6: Extract chart JSON from Data Analyst output
    # ------------------------------
    print("Extracting chart specifications from Analyst agent...")
    try:
        # tasks_output[1] => second task (Data Analyst), .raw holds its full text output
        analysis_output = result.tasks_output[1].raw
    except Exception as e:
        print("Could not access analyst task output via tasks_output:", e)
        # Fallback: use whole crew raw output (you'll still at least have text)
        analysis_output = result.raw

    try:
        json_block = analysis_output.split("```json")[1].split("```")[0]
    except Exception:
        print("Could not extract JSON chart spec. No charts will be generated.")
        json_block = '{"charts": []}'

    # ------------------------------
    # Step 7: Generate AI-selected charts dynamically
    # ------------------------------
    print("Generating dynamic charts selected by AI...")
    chart_paths = generate_charts_from_spec(kpi_df, json_block, str(charts_dir))

    print("Generated Charts:")
    for p in chart_paths:
        print("  -", p)

    # ------------------------------
    # Step 8: Final pass (Insights Writer)
    # ------------------------------
    print("Running final insights generation with chart references...")
    # final_inputs = {
    #     **inputs,
    #     "chart_paths": "\n".join(chart_paths),
    # }
    #
    # final_result = crew.kickoff(inputs=final_inputs)

    final_markdown = str(result)
    report_path = reports_dir / "kpi_insights_report.md"
    report_path.write_text(final_markdown, encoding="utf-8")

    print(f"\n✅ FINAL REPORT SAVED TO: {report_path}")
    print(f"📊 CHARTS SAVED TO: {charts_dir}")

    return "".join(result.raw)