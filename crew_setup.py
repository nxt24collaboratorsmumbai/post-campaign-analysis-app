import os
from crewai import Agent, Task, Crew, Process


def build_agents(model: str | None = None):
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    campaign_manager = Agent(
        role="Post-Campaign Manager",
        goal=(
            "Validate the KPI integrity (lands, cost, HVEA, channel) and describe how "
            "they should be interpreted for a post-campaign analysis."
        ),
        backstory=(
            "You are an experienced campaign strategist with deep understanding of "
            "media channels, KPI interpretation, measurement logic and data quality. "
            "You ensure the analysis to follow is based on accurate KPI mapping and "
            "good campaign context."
        ),
        verbose=True,
        llm=model_name,
    )

    data_analyst = Agent(
        role="KPI Data Analyst",
        goal=(
            "Analyze the KPI dataset and propose 4–6 meaningful chart specifications "
            "as JSON objects, based on data patterns. You focus on clarity and efficiency."
        ),
        backstory=(
            "You are a seasoned performance analytics professional who identifies KPI "
            "relationships such as efficiency, channel performance, and optimization signals. "
            "You know how to choose the right visualization for each insight."
        ),
        verbose=True,
        llm=model_name,
    )

    insights_writer = Agent(
        role="Insights & Strategy Specialist",
        goal=(
            "Turn KPI behavior, visualizations, and analyst findings into a clear, "
            "actionable PCA insights narrative with strong recommendations."
        ),
        backstory=(
            "You specialize in translating analytical patterns into narrative insights "
            "that drive better media planning, optimization, and strategic actions."
        ),
        verbose=True,
        llm=model_name,
    )

    return campaign_manager, data_analyst, insights_writer


def build_tasks(campaign_manager, data_analyst, insights_writer):

    # --------------------- Task 1: Campaign Manager -------------------------
    scope_task = Task(
        description=(
            "You validate KPI readiness for PCA.\n\n"
            "KPI MAPPING:\n{kpi_mapping}\n\n"
            "FILE OVERVIEW:\n{file_overview}\n\n"
            "Your responsibilities:\n"
            "- Verify KPI mapping (lands, cost, HVEA, channel)\n"
            "- Identify missing/weak KPI columns\n"
            "- Provide short interpretation guidance\n"
            "- Suggest filters/groupings\n\n"
            "KEEP ANSWER UNDER 250 WORDS.\n"
            "Return markdown with:\n"
            "## KPI Validation\n"
            "## Missing KPIs\n"
            "## Interpretation Guidance\n"
            "## Suggested Filters"
        ),
        expected_output=(
            "A concise markdown summary validating KPI mapping, identifying missing KPIs, "
            "giving interpretation guidance and suggesting PCA-prep filters."
        ),
        agent=campaign_manager,
    )

    # --------------------- Task 2: Data Analyst ----------------------------
    analysis_task = Task(
        description=(
            "Analyze ONLY KPI columns: lands, cost, HVEA and group them by channels.\n\n"
            "You get:\n"
            "- SCHEMA SUMMARY\n{schema_summary}\n\n"
            "- NUMERIC SUMMARY\n{numeric_summary}\n\n"
            "- CATEGORICAL SUMMARY\n{categorical_summary}\n\n"
            "- SAMPLE ROWS\n{sample_rows}\n\n"
            "Your responsibilities:\n"
            "- Provide KPI behavior analysis\n"
            "- Discuss relationships (cost→lands efficiency, channel differences)\n"
            "- Identify data quality issues\n"
            "- Propose **4–6 chart specifications** as JSON, good if we have bar or line charts as per data file\n\n"
            "Format JSON EXACTLY like:\n"
            "```json\n"
            "{ \"charts\": [ {\"type\": \"bar\", \"x\": \"channel\", \"y\": \"lands\", \"title\": \"...\"}, ... ] }\n"
            "```\n\n"
            "Allowed chart types: bar, line, scatter, box, stacked_bar, funnel.\n"
            "KEEP ANSWER UNDER 500 WORDS."
        ),
        expected_output=(
            "A KPI analysis summary AND a JSON block containing 4–6 chart specifications "
            "under the key 'charts'."
        ),
        agent=data_analyst,
        context=[scope_task],
    )

    # --------------------- Task 3: Insights Writer -------------------------
    insights_task = Task(
        description=(
            "Create a PCA insights report using:\n"
            "- Campaign Manager's KPI validation\n"
            "- Data Analyst KPI findings\n"
            "- Generated chart images at paths:\n{chart_paths}\n\n"
            "Produce markdown with:\n"
            "## Executive Summary\n"
            "## Key KPI Insights\n"
            "## Channel Performance Story\n"
            "## Visualization Interpretation\n"
            "## Recommendations\n\n"
            "Focus on narrative depth (700–900 words)."
        ),
        expected_output=(
            "A PCA-style insights report summarizing KPI findings, referencing charts, "
            "and providing actionable recommendations."
        ),
        agent=insights_writer,
        context=[scope_task, analysis_task],
    )

    return scope_task, analysis_task, insights_task


def build_crew(model=None):
    c, a, i = build_agents(model)
    t1, t2, t3 = build_tasks(c, a, i)

    return Crew(
        agents=[c, a, i],
        tasks=[t1, t2, t3],
        process=Process.sequential,
        verbose=True,
    )
