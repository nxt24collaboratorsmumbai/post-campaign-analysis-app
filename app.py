import base64
import os
import replicate
from crewai import Agent, Task

from generator import (
    generate_insights_from_image
)

import streamlit as st
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

#Configure page
st.set_page_config(page_title="Agentic Post Campaign Analysis", layout="wide")

# Header
st.title("🧠 Agentic Post Campaign Analysis")

uploaded_file = st.file_uploader(
    "Upload a file (optional):",
    type=["png", "jpg", "jpeg", "pdf", "csv", "xlsx"],
    help="Upload campaign dashboard snapshots or related files."
)

if uploaded_file is not None:
    st.success(f"File '{uploaded_file.name}' uploaded successfully!")
    #st.image(uploaded_file, caption=uploaded_file.name, use_column_width=True)

# User input
prompt = st.text_area("Enter your prompt:", placeholder="Ask me something...")


if st.button("Generate Response"):
    # if not replicate_token:
    #     st.error("Missing Replicate API key. Please set REPLICATE_API_TOKEN in .env.")
    if not prompt.strip() and uploaded_file is None:
        st.warning("Please enter a prompt or upload a file.")
    else:

        with st.spinner("🧠 Generating insights..."):

            insights = generate_insights_from_image(uploaded_file, prompt)

            # print(prompt)
            st.subheader("Response:")
            st.write(insights)







# import base64
# import os
# import replicate
# from crewai import Agent, Task, Crew
#
# import streamlit as st
# from PIL import Image
# from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI
#
# load_dotenv()
# REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
#
# # Define the LLM (using a simple model for this example)
# llm = ChatOpenAI(model="gpt-4.0", temperature=0.7)
#
# image_analyst = Agent(
#     role="Image Intelligence Analyst (Dashboard & Visual Analytics Specialist)",
#     goal="Interpret visual dashboards, charts, and campaign performance screenshots to extract clear, data-backed insights on trends, KPIs, and anomalies.",
#     backstory="A senior Business Intelligence (BI) and marketing analytics specialist who has spent years analyzing campaign dashboards from tools like Google Analytics, Meta Ads Manager, and Tableau. Expert at reading visual data (charts, graphs, KPIs) and converting them into concise, human-readable insights for strategic reports.",
#     llm="gpt-4o"  # or your chosen model
# )
#
# # data_analyst = Agent(
# #     role="Campaign Performance Data Analyst",
# #     goal="Analyze campaign CSV data for performance trends and key insights.",
# #     backstory="An experienced marketing data scientist who extracts insights from metrics like CTR, CPC, ROI, and engagement rates.",
# #     llm="gpt-4o"
# # )
#
#
# # image_analysis_task = Task(
# #     description="Analyze the uploaded campaign dashboard or chart image. Identify and interpret visible metrics, performance patterns, and anomalies. Translate visual elements into structured textual insights — including trend explanations and key metric takeaways.",
# #     expected_output="A structured summary containing: Overview: What the visual represents (metric type, time period, channels).Key KPIs & Values: Extract and label all visible metrics.Trends & Patterns: Describe noticeable movements (e.g., rising CTR, declining conversions).Anomalies / Highlights: Identify spikes, dips, or unexpected results.Visual Insight Summary: A concise 3–5 line summary suitable for inclusion in a post-campaign PPT slide.",
# #     agent=image_analyst
# # )
#
# image_analysis_task = Task(
#     description="Analyze the uploaded campaign dashboard image. Extract all visible KPIs, trends, and anomalies, then summarize insights in a structured, slide-ready format.",
#     expected_output="""
# {
#   "overview": "Short text describing what the dashboard shows",
#   "key_kpis": [{"metric": "CTR", "value": "3.8%"}, {"metric": "CPC", "value": "$1.12"}, ...],
#   "trends": ["CTR increased steadily over the week", "Conversion rate dipped mid-campaign"],
#   "anomalies": ["Sharp CTR drop on 12th May due to budget cap"],
#   "summary": "The campaign showed consistent engagement growth with slight conversion fluctuation; overall positive trend."
# }
# """,
#     agent=image_analyst
# )
#
#
# # data_analysis_task = Task(
# #     description="Analyze the provided CSV data and extract key metrics, performance summaries, and trends.",
# #     expected_output="A paragraph or bullet list of insights and analysis points from the image.",
# #     agent=data_analyst
# # )
#
#
#
#
#
#
# def load_prompt(template_path, **kwargs):
#     with open(template_path, "r") as file:
#         template = file.read()
#     return template.format(**kwargs)
#
# # Define the CrewAI agent
# # image_agent = Agent(
# #     role="Image Specialist",
# #     goal="Analyze campaign snapshot image and return clear text insights",
# #     backstory="Expert in post-campaign marketing performance analysis using dashboards, charts, and data visuals.",
# #     llm=llm
# # )
#
# def generate_insights_from_image(image_file, user_prompt) -> str:
#     img_bytes = image_file.getvalue()
#     base64_img = base64.b64encode(img_bytes).decode("utf-8")
#     data_uri = f"data:image/jpeg;base64,{base64_img}"
#
#     st.write("🧠 Generating insights...")
#
#     input_prompt = load_prompt(
#         "image_to_text_prompt.txt",
#         campaign_context=user_prompt
#     )
#
#     # Define the task
#     # analysis_task = Task(
#     #     description=(
#     #         f"Analyze this post-campaign dashboard image. "
#     #         f"Extract insights, key performance metrics, trends, anomalies, and recommendations.\n"
#     #         f"Context: {user_prompt}"
#     #     ),
#     #     agent=image_agent,
#     #     expected_output="A paragraph or bullet list of insights and analysis points from the image."
#     # )
#
#     # Create and run the crew
#     crew = Crew(agents=[image_analyst], tasks=[image_analysis_task])
#     result = crew.kickoff(inputs={"image_data_uri": data_uri, "prompt": input_prompt})
#
#     return result
#
# # Streamlit UI
# st.set_page_config(page_title="Agentic Post Campaign Analysis", layout="wide")
# st.title("🧠 Agentic Post Campaign Analysis")
#
# uploaded_file = st.file_uploader(
#     "Upload a file (optional):",
#     type=["png", "jpg", "jpeg"],
#     help="Upload campaign dashboard snapshots or related visuals."
# )
#
# if uploaded_file is not None:
#     st.success(f"File '{uploaded_file.name}' uploaded successfully!")
#     st.image(uploaded_file, caption=uploaded_file.name, use_column_width=True)
#
# prompt = st.text_area("Enter campaign context or question:", placeholder="e.g. Identify performance drop areas or top channels")
#
# if st.button("Generate Insights"):
#     if not prompt.strip() and uploaded_file is None:
#         st.warning("Please enter a prompt or upload a file.")
#     else:
#         with st.spinner("Analyzing and generating insights..."):
#             insights = generate_insights_from_image(uploaded_file, prompt)
#             st.subheader("Insights:")
#             st.write(insights.raw)


