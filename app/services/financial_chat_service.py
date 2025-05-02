# from crewai import Agent, Task, Crew, Process, LLM
# from typing import List, Dict, Any, Optional
# import os
# from dotenv import load_dotenv
# from ..models.schemas import ChatResponse
# from datetime import datetime
# import json
# import asyncio
# import re
# import logging
# from ..tools.search_query import CustomSearchTool
# from crewai.tools import tool
# from ..database.connection import get_db
# from ..database.models import User, Portfolio
# from sqlalchemy.orm import Session
# from ..services.portfolio_service import get_user_portfolios
#
# # Import Guardrails libraries
# from guardrails import Guard
# from guardrails.validators import Validator, PassResult, FailResult
#
# # Configure logging for debugging and tracking
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.StreamHandler(),
#         logging.FileHandler('financial_advice.log')
#     ]
# )
# logger = logging.getLogger(__name__)
#
# # Create a separate logger for guardrails
# guardrails_logger = logging.getLogger("financial_guardrails")
# guardrails_logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
# guardrails_logger.addHandler(handler)
#
# # Load environment variables
# load_dotenv()
#
# # Initialize LLM for the agents using OpenAI ChatGPT and Gemini for other tasks.
# llm = LLM(
#     model='openai/gpt-3.5-turbo',
#     api_key=os.getenv("OPENAI_API_KEY")
# )
# llm1 = LLM(
#     model='gemini/gemini-2.0-flash',
#     api_key=os.getenv("GEMINI_API_KEY")
# )
#
#
# # Define tools
# @tool("view_user_portfolio")
# def view_user_portfolio(user_id: int) -> str:
#     """
#     Retrieve investment portfolio data for a specific user.
#     Returns a JSON string with portfolio details or an error message.
#     """
#     logger.info(f"Fetching portfolio for user_id: {user_id}")
#     try:
#         db = next(get_db())
#         portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
#
#         if not portfolio:
#             logger.warning(f"No portfolio found for user_id: {user_id}")
#             return json.dumps({
#                 "error": "No portfolio found for this user",
#                 "portfolio": None
#             })
#
#         # Parse portfolio data
#         portfolio_data = {
#             "id": portfolio.id,
#             "user_id": portfolio.user_id,
#             "asset_allocation": json.loads(portfolio.portfolio_json).get('asset_allocation', {}),
#             "performance_projection": json.loads(portfolio.portfolio_json).get('performance_projection', {}),
#             "risk_assessment": json.loads(portfolio.portfolio_json).get('risk_analysis', {}),
#             "created_at": portfolio.created_at.isoformat(),
#         }
#         logger.info(f"Portfolio retrieved successfully for user_id: {user_id}")
#         return json.dumps({
#             "portfolio": portfolio_data
#         })
#     except Exception as e:
#         logger.error(f"Error fetching portfolio for user_id {user_id}: {str(e)}")
#         return json.dumps({
#             "error": str(e),
#             "portfolio": None
#         })
#
#
# @tool("financial_research")
# def financial_research_tool(query: str) -> str:
#     """
#     Perform financial research specific to Indian markets using a custom search tool.
#     Returns a JSON string with research findings.
#     """
#     logger.info(f"Performing financial research for query: {query}")
#     try:
#         search_tool = CustomSearchTool()
#         results = search_tool._run(
#             query=query,
#             limit=5,
#             lang="en",
#             timeout=60000
#         )
#
#         # Initialize response structure
#         formatted_results = {
#             "research": {
#                 "sources": [],
#                 "key_findings": [],
#                 "data_points": []
#             }
#         }
#
#         # Process search results
#         if isinstance(results, list):
#             for result in results:
#                 if isinstance(result, dict):
#                     formatted_results["research"]["sources"].append(result.get("url", ""))
#                     formatted_results["research"]["key_findings"].append(result.get("content", ""))
#                     formatted_results["research"]["data_points"].append({
#                         "url": result.get("url", ""),
#                         "content": result.get("content", "")
#                     })
#         logger.info(f"Research completed for query: {query}")
#         return json.dumps(formatted_results)
#     except Exception as e:
#         logger.error(f"Error in financial research for query '{query}': {str(e)}")
#         return json.dumps({
#             "research": {
#                 "sources": [],
#                 "key_findings": [],
#                 "data_points": []
#             }
#         })
#
#
# # Define agents
# classifier = Agent(
#     role='Query Classifier',
#     goal='Categorize user queries to determine if they are financial, portfolio-related, or irrelevant',
#     backstory="""You are an expert in analyzing user queries. You excel at distinguishing financial queries (e.g., stock prices, portfolio questions) from greetings (e.g., 'Hello') or general questions (e.g., 'What's the weather?'). Your role is to ensure only relevant financial queries are processed.""",
#     verbose=True,
#     llm=llm
# )
#
# researcher = Agent(
#     role='Indian Financial Market Researcher',
#     goal='Gather and analyze financial information specific to Indian markets',
#     backstory="""You are an expert financial researcher specializing in Indian markets with deep knowledge of SEBI regulations, market dynamics, and financial terminology. You use tools to collect and verify information relevant to Indian investors, avoiding unnecessary searches for straightforward queries.""",
#     tools=[financial_research_tool, view_user_portfolio],
#     verbose=True,
#     llm=llm1
# )
#
# advisor = Agent(
#     role='Indian Financial Advisor',
#     goal='Provide accurate and helpful financial advice for Indian investors',
#     backstory="""You are a certified financial advisor with expertise in Indian personal finance, SEBI regulations, tax laws, and market conditions. You analyze research data to deliver clear, actionable advice tailored for Indian investors, ensuring responses are professional and confident.""",
#     tools=[view_user_portfolio],
#     verbose=True,
#     llm=llm1
# )
#
# # Classification task with four possible query categories
# classify_task = Task(
#     description="""
#         Analyze the user query to categorize it as one of:
#         - 'irrelevant': Queries like greetings or non-financial topics (e.g., "Hi", "Hello", "How is the weather?", etc.).
#         - 'conceptual': Financial queries asking for definitions or explanations (e.g., "What is an IPO?", "What is the P/E ratio?", "What do you mean by investment?", "What is the debt/equity ratio?", "What is earnings per share?", etc.).
#         - 'real_time': Financial queries that require current data and internet access (e.g., "What is the current stock price?", "Give me the mutual funds with 20% YOY", etc.). Use Gemini directly for this category.
#         - 'portfolio': Queries specific to a user's portfolio (e.g., "What's my asset allocation?").
#
#         Query: {query}
#
#         Guidelines:
#         - Classify greetings and non-financial questions as 'irrelevant'.
#         - Questions asking for definitions or explanations (like those about IPOs, investment, P/E ratio, etc.) are 'conceptual'.
#         - Questions requiring current data (like stock prices, mutual funds performance, etc.) are 'real_time' and should be handled by Gemini.
#         - Portfolio related queries include any reference to "my portfolio", "asset allocation", or user-specific investments.
#         - If ambiguous, lean towards categorizing it as a financial query.
#
#         Return a JSON object:
#         {{
#             "query_type": "irrelevant|conceptual|real_time|portfolio"
#         }}
#     """,
#     expected_output="A JSON object specifying the query type",
#     agent=classifier
# )
#
# research_task = Task(
#     description="""
#         Research the financial query using available tools, focusing on Indian markets.
#
#         Query: {query}
#         User ID: {user_id}
#
#         Requirements:
#         1. Use the financial_research_tool for market-related queries.
#         2. Use view_user_portfolio for portfolio-related queries with user_id={user_id}.
#         3. Gather data from Indian financial sources.
#         4. Verify information accuracy against Indian market data.
#         5. Organize findings by topic.
#
#         Return a JSON object:
#         {{
#             "research": {{
#                 "sources": ["Source 1", "Source 2"],
#                 "key_findings": ["Finding 1", "Finding 2"],
#                 "data_points": ["Data 1", "Data 2"]
#             }}
#         }}
#     """,
#     expected_output="Research findings with sources and data points",
#     agent=researcher
# )
#
# advice_task = Task(
#     description="""
#         Provide financial advice based on research findings for Indian markets, tailored to the query type.
#
#         Query: {query}
#         User ID: {user_id}
#         Query Type: {query_type}
#
#         Requirements:
#         1. For 'financial' queries, analyze research findings and provide market-specific advice.
#         2. For 'portfolio' queries, use view_user_portfolio with user_id={user_id} and focus on user-specific advice.
#         3. For 'irrelevant' queries, return a polite rejection in the same JSON format.
#         4. Provide clear, actionable advice for financial/portfolio queries.
#         5. Support recommendations with Indian market data and consider tax/regulatory implications.
#         6. Be confident and specific in recommendations without disclaimers.
#         7. Use the following JSON structure:
#         {{
#             "advice": {{
#                 "analysis": "Detailed analysis or rejection message",
#                 "recommendations": ["Recommendation 1", "Recommendation 2"],
#                 "supporting_data": ["Data point 1", "Data point 2"],
#                 "sources": ["Source 1", "Source 2"]
#             }}
#         }}
#     """,
#     expected_output="Financial advice or rejection message in JSON format",
#     agent=advisor,
#     context=[research_task]
# )
#
# # Create crews
# classification_crew = Crew(
#     agents=[classifier],
#     tasks=[classify_task],
#     verbose=1,
#     process=Process.sequential
# )
#
# chat_crew = Crew(
#     agents=[researcher, advisor],
#     tasks=[research_task, advice_task],
#     verbose=1,
#     process=Process.sequential
# )
#
# # Define custom validators using guardrails' Validator interface
# class MinLengthValidator(Validator):
#     name = "min-length"
#
#     def validate(self, value, metadata):
#         min_length = int(metadata.get('min', 10))
#         default_message = metadata.get('default_message',
#                                        "I'm sorry, but I couldn't generate an appropriate response. Please try again later.")
#         if len(value.strip()) < min_length:
#             return FailResult(error_message="Response too short", fix_value=default_message)
#         return PassResult()
#
#
# class DisallowedTermsValidator(Validator):
#     name = "disallowed-terms"
#
#     def validate(self, value, metadata):
#         terms = metadata.get('terms', '').split(',')
#         disallowed = [term.strip().lower() for term in terms]
#         censored_value = value
#         for term in disallowed:
#             pattern = r'\b' + re.escape(term) + r'\b'
#             if re.search(pattern, value, re.IGNORECASE):
#                 censored_value = re.sub(pattern, '[censored]', censored_value, flags=re.IGNORECASE)
#         if censored_value != value:
#             return FailResult(error_message="Disallowed terms found", fix_value=censored_value)
#         return PassResult()
#
#
# # Define RAIL (Guardrails) specifications for advice and conceptual queries
# advice_rail_str = """
# <rail version="0.1">
# <output>
#     <object name="advice">
#         <string
#             name="analysis"
#             description="Detailed analysis or rejection message"
#             format="min-length: min=10 default_message='I''m sorry, but I couldn''t generate an appropriate response. Please try again later.'; disallowed-terms: terms='not financial advice,shit,speculation'"
#             on-fail-min-length="fix"
#             on-fail-disallowed-terms="fix"
#         />
#         <list name="recommendations" description="List of recommendations" />
#         <list name="supporting_data" description="List of supporting data points" />
#         <list name="sources" description="List of sources" />
#     </object>
# </output>
# <prompt>
# Provide financial advice based on the query.
# </prompt>
# </rail>
# """
#
# conceptual_rail_str = """
# <rail version="0.1">
# <output>
#     <string
#         name="answer"
#         description="Response to conceptual query"
#         format="min-length: min=10 default_message='I''m sorry, but I couldn''t generate an appropriate response. Please try again later.'; disallowed-terms: terms='not financial advice,shit,speculation'"
#         on-fail-min-length="fix"
#         on-fail-disallowed-terms="fix"
#     />
# </output>
# <prompt>
# {query}
# </prompt>
# </rail>
# """
#
# # Create Guard objects from RAIL strings (note: remove custom_validators if unsupported in your version)
# advice_guard = Guard.from_rail_string(advice_rail_str)
# conceptual_guard = Guard.from_rail_string(conceptual_rail_str)
#
#
# def _clean_json_response(result_content: str) -> str:
#     """
#     Clean and extract valid JSON from crew output to ensure parseability.
#     """
#     logger.debug(f"Cleaning JSON response: {result_content[:100]}...")
#     if not result_content.strip().startswith('{'):
#         result_content = re.sub(r'```(?:json)?\s*|\s*```', '', result_content)
#         json_match = re.search(r'\{.*\}', result_content, re.DOTALL)
#         if json_match:
#             result_content = json_match.group()
#     result_content = result_content.strip()
#     try:
#         json_obj = json.loads(result_content)
#         return json.dumps(json_obj)
#     except json.JSONDecodeError as e:
#         logger.error(f"JSON cleaning failed: {str(e)}")
#         if "Extra data" in str(e):
#             position = int(re.search(r'char (\d+)', str(e)).group(1))
#             return result_content[:position]
#         return result_content
#
#
# # --- Speculation Removal Code ---
# class SpeculationRemover:
#     """Utility to detect and remove speculative language from financial advice"""
#     def __init__(self):
#         self.disallowed_terms = [
#             "not financial advice",
#             "shit",
#             "speculation",
#             "might be",
#             "could potentially",
#             "possibly",
#             "maybe",
#             "uncertain",
#             "we think",
#             "we believe",
#             "we expect",
#             "unclear",
#             "not sure",
#             "can't predict",
#             "unpredictable",
#             "may or may not",
#             "gamble",
#             "bet",
#             "it seems",
#             "appears to be",
#             "could be",
#             "is likely",
#             "probably",
#             "projected to",
#             "anticipated",
#             "estimated",
#             "forecasted",
#             "guessed",
#             "potential",
#             "possibility of",
#             "chance of",
#             "risk of",
#             "speculated",
#             "not guaranteed",
#             "take a chance",
#             "depends on market conditions"
#         ]
#         self.replacements = {
#             r'\bnot financial advice\b': "This is factual financial information",
#             r'\bshit\b': "[inappropriate term]",
#             r'\bspeculation\b': "analysis",
#             r'\bmight be\b': "is",
#             r'\bcould potentially\b': "will",
#             r'\bpossibly\b': "definitely",
#             r'\bmaybe\b': "will",
#             r'\buncertain\b': "certain",
#             r'\bwe think\b': "analysis shows",
#             r'\bwe believe\b': "data indicates",
#             r'\bwe expect\b': "projections show",
#             r'\bunclear\b': "clear",
#             r'\bnot sure\b': "confident",
#             r'\bcan\'t predict\b': "can determine",
#             r'\bunpredictable\b': "analyzable",
#             r'\bmay or may not\b': "will",
#             r'\bgamble\b': "invest strategically",
#             r'\bbet\b': "strategic investment",
#             r'\bit seems\b': "it is",
#             r'\bappears to be\b': "is",
#             r'\bcould be\b': "is",
#             r'\bis likely\b': "is",
#             r'\bprobably\b': "definitely",
#             r'\bprojected to\b': "will",
#             r'\banticipated\b': "expected",
#             r'\bestimated\b': "calculated",
#             r'\bforecasted\b': "determined",
#             r'\bguessed\b': "calculated",
#             r'\bpotential\b': "certain",
#             r'\bpossibility of\b': "certainty of",
#             r'\bchance of\b': "certainty of",
#             r'\brisk of\b': "understood impact of",
#             r'\bspeculated\b': "analyzed",
#             r'\bnot guaranteed\b': "assured",
#             r'\btake a chance\b': "make a strategic decision",
#             r'\bdepends on market conditions\b': "has clear criteria for success"
#         }
#
#     def remove_speculation(self, text):
#         if not isinstance(text, str) or not text:
#             return text if text is not None else ""
#         result = text
#         for pattern, replacement in self.replacements.items():
#             result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
#         return result
#
#
# # Process response through guardrails and speculation removal
# async def process_response_with_guardrails(response_data, query_type):
#     """
#     Process a response through guardrails and remove speculation.
#     Handles both conceptual (plain text) and financial/portfolio (structured advice) responses.
#     """
#     logger.info(f"Processing response through guardrails for query type: {query_type}")
#     try:
#         remover = SpeculationRemover()
#         if query_type == 'conceptual':
#             # Extract the string answer if response_data is a dict.
#             if isinstance(response_data, dict):
#                 response_str = response_data.get('answer', '')
#             else:
#                 response_str = response_data
#             if not isinstance(response_str, str):
#                 response_str = str(response_str)
#             # Validate using conceptual guard.
#             validated_output = conceptual_guard.validate(response_str)
#             # The validated output is a plain string.
#             answer = validated_output
#             answer = remover.remove_speculation(answer)
#             return ChatResponse(
#                 answer=answer,
#                 recommendations=[],
#                 supporting_data=[],
#                 sources=[],
#                 timestamp=datetime.now()
#             )
#         else:
#             # For financial/portfolio queries, we expect a structured response.
#             # If response_data is a dict, serialize it.
#             if isinstance(response_data, dict):
#                 cleaned_input = json.dumps(response_data)
#             else:
#                 cleaned_input = response_data
#             # Validate using the advice guard.
#             validated_output = advice_guard.validate(cleaned_input)
#             # validated_output is a string; parse it into a dictionary.
#             try:
#                 advice_dict = json.loads(validated_output)
#             except Exception as e:
#                 logger.error(f"Error parsing validated output as JSON: {str(e)}")
#                 advice_dict = {}
#             if 'advice' in advice_dict:
#                 advice = advice_dict['advice']
#                 analysis = remover.remove_speculation(advice.get('analysis', 'No advice available'))
#                 recommendations = [remover.remove_speculation(rec) for rec in advice.get('recommendations', [])]
#                 supporting_data = [remover.remove_speculation(data) for data in advice.get('supporting_data', [])]
#                 sources = advice.get('sources', [])
#                 return ChatResponse(
#                     answer=analysis,
#                     recommendations=recommendations,
#                     supporting_data=supporting_data,
#                     sources=sources,
#                     timestamp=datetime.now()
#                 )
#             else:
#                 fallback_response = remover.remove_speculation(
#                     validated_output if isinstance(validated_output, str) else str(validated_output)
#                 )
#                 return ChatResponse(
#                     answer=fallback_response,
#                     recommendations=[],
#                     supporting_data=[],
#                     sources=[],
#                     timestamp=datetime.now()
#                 )
#     except Exception as e:
#         logger.error(f"Error in processing response with guardrails: {str(e)}")
#         return ChatResponse(
#             answer="I apologize for the technical difficulties. Let me try to answer your query more simply.",
#             recommendations=[],
#             supporting_data=[],
#             sources=[],
#             timestamp=datetime.now()
#         )
#
#
# def clean_financial_advice(advice_dict):
#     """
#     Clean speculation from a financial advice dictionary.
#     """
#     if not isinstance(advice_dict, dict) or 'advice' not in advice_dict:
#         return advice_dict
#     remover = SpeculationRemover()
#     advice = advice_dict['advice']
#     try:
#         if 'analysis' in advice and advice['analysis']:
#             advice['analysis'] = remover.remove_speculation(advice['analysis'])
#         if 'recommendations' in advice and isinstance(advice['recommendations'], list):
#             advice['recommendations'] = [
#                 remover.remove_speculation(item) if isinstance(item, str) and item else item
#                 for item in advice['recommendations']
#             ]
#         if 'supporting_data' in advice and isinstance(advice['supporting_data'], list):
#             advice['supporting_data'] = [
#                 remover.remove_speculation(item) if isinstance(item, str) and item else item
#                 for item in advice['supporting_data']
#             ]
#         guardrails_logger.info("Successfully cleaned speculation from advice dictionary")
#         return advice_dict
#     except Exception as e:
#         guardrails_logger.error(f"Error cleaning advice dictionary: {str(e)}")
#         return advice_dict
#
#
# # Main function to process financial queries
# async def get_financial_advice(query: str, user_id: Optional[int] = None) -> ChatResponse:
#     """
#     Process a user query to provide financial advice or reject irrelevant queries.
#     Applies guardrails and removes speculation for confident, accurate answers.
#     """
#     logger.info(f"Processing query: '{query}' for user_id: {user_id}")
#     loop = None
#     try:
#         # Step 1: Classify the query
#         logger.debug("Running query classification")
#         classification_result = classification_crew.kickoff(inputs={'query': query})
#         try:
#             classification_content = (
#                 classification_result.tasks[-1].output
#                 if hasattr(classification_result, 'tasks') and classification_result.tasks
#                 else str(classification_result)
#             )
#             cleaned_classification = _clean_json_response(classification_content)
#             query_type = json.loads(cleaned_classification).get('query_type', 'financial')
#             logger.info(f"Query classified as: {query_type}")
#         except (json.JSONDecodeError, AttributeError) as e:
#             logger.warning(f"Classification parsing failed: {str(e)}. Defaulting to 'financial'")
#             query_type = 'financial'
#
#         if query_type == 'irrelevant':
#             logger.info("Query is irrelevant; returning rejection response")
#             return ChatResponse(
#                 answer="I'm a financial analyst and can only assist with financial queries.",
#                 recommendations=[],
#                 supporting_data=[],
#                 sources=[],
#                 timestamp=datetime.now()
#             )
#
#         if query_type == 'conceptual':
#             logger.info("Query is conceptual; generating response using Gemini")
#             from google import genai
#             gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
#             enhanced_prompt = f"""
#             You are a confident financial expert specializing in Indian markets.
#             Provide a clear, factual, and definitive explanation for the following financial concept.
#             Avoid uncertain language - be authoritative and precise.
#
#             Query: {query}
#             """
#             response = gemini_client.models.generate_content(
#                 model="gemini-2.0-flash",
#                 contents=enhanced_prompt
#             )
#             full_text = response.text
#             return await process_response_with_guardrails(full_text, 'conceptual')
#
#         # For financial and portfolio queries, prepare inputs
#         inputs = {
#             'query': query,
#             'user_id': user_id,
#             'query_type': query_type
#         }
#         logger.debug(f"Prepared inputs: {inputs}")
#
#         if user_id:
#             try:
#                 db = next(get_db())
#                 portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
#                 if portfolio:
#                     portfolio_data = {
#                         "asset_allocation": json.loads(portfolio.portfolio_json).get('asset_allocation', {}),
#                         "risk_assessment": json.loads(portfolio.portfolio_json).get('risk_analysis', {}),
#                         "performance_projection": json.loads(portfolio.portfolio_json).get('performance_projection', {})
#                     }
#                     inputs['portfolio_data'] = json.dumps(portfolio_data)
#                     logger.info(f"Portfolio data added for user_id: {user_id}")
#             except Exception as e:
#                 logger.error(f"Error fetching portfolio data: {str(e)}")
#
#         logger.debug("Starting chat crew execution")
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         try:
#             if query_type == 'real_time':
#                 inputs['query'] = f"IMPORTANT: Provide definitive, factual information without qualifiers or speculation. {query}"
#             result = chat_crew.kickoff(inputs=inputs)
#             if hasattr(result, 'tasks') and result.tasks:
#                 result_content = result.tasks[-1].output
#             else:
#                 result_content = str(result)
#                 logger.warning("No tasks found in result; using stringified output")
#             cleaned_json = _clean_json_response(result_content)
#             try:
#                 advice_data = json.loads(cleaned_json)
#                 return await process_response_with_guardrails(advice_data, query_type)
#             except json.JSONDecodeError as e:
#                 logger.error(f"JSON parsing failed: {str(e)}. Raw: {result_content}")
#                 return await process_response_with_guardrails(result_content, query_type)
#         finally:
#             if loop:
#                 loop.close()
#                 logger.debug("Event loop closed")
#     except Exception as e:
#         logger.error(f"Unexpected error in get_financial_advice: {str(e)}")
#         return ChatResponse(
#             answer="I apologize, but I'm having trouble processing your request. Please try again.",
#             recommendations=[],
#             supporting_data=[],
#             sources=[],
#             timestamp=datetime.now()
#         )
#
#
#
#
#
#
#










# Latest Code
#
from crewai import Agent, Task, Crew, Process, LLM
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from ..models.schemas import ChatResponse
from datetime import datetime
import json
import asyncio
import re
import logging
from ..tools.search_query import CustomSearchTool
from crewai.tools import tool
from ..database.connection import get_db
from ..database.models import User, Portfolio
from sqlalchemy.orm import Session
from ..services.portfolio_service import get_user_portfolios

# Configure logging for debugging and tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('financial_advice.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize LLM for the agents using OpenAI ChatGPT and Gemini for other tasks.
llm = LLM(
    model='openai/gpt-3.5-turbo',
    api_key=os.getenv("OPENAI_API_KEY")
)
llm1 = LLM(
    model='gemini/gemini-2.0-flash',
    api_key=os.getenv("GEMINI_API_KEY")
)


try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    logger.warning("Google Generative AI package not available. Using fallback for conceptual queries.")
    GENAI_AVAILABLE = False


# Define tools
@tool("view_user_portfolio")
def view_user_portfolio(user_id: int) -> str:
    """
    Retrieve investment portfolio data for a specific user.
    Returns a JSON string with portfolio details or an error message.
    """
    logger.info(f"Fetching portfolio for user_id: {user_id}")
    try:
        db = next(get_db())
        portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()

        if not portfolio:
            logger.warning(f"No portfolio found for user_id: {user_id}")
            return json.dumps({
                "error": "No portfolio found for this user",
                "portfolio": None
            })

        # Parse portfolio data
        portfolio_data = {
            "id": portfolio.id,
            "user_id": portfolio.user_id,
            "asset_allocation": json.loads(portfolio.portfolio_json).get('asset_allocation', {}),
            "performance_projection": json.loads(portfolio.portfolio_json).get('performance_projection', {}),
            "risk_assessment": json.loads(portfolio.portfolio_json).get('risk_analysis', {}),
            "created_at": portfolio.created_at.isoformat(),
        }
        logger.info(f"Portfolio retrieved successfully for user_id: {user_id}")
        return json.dumps({
            "portfolio": portfolio_data
        })
    except Exception as e:
        logger.error(f"Error fetching portfolio for user_id {user_id}: {str(e)}")
        return json.dumps({
            "error": str(e),
            "portfolio": None
        })


@tool("financial_research")
def financial_research_tool(query: str) -> str:
    """
    Perform financial research specific to Indian markets using a custom search tool.
    Returns a JSON string with research findings.
    """
    logger.info(f"Performing financial research for query: {query}")
    try:
        search_tool = CustomSearchTool()
        results = search_tool._run(
            query=query,
            limit=5,
            lang="en",
            timeout=60000
        )

        # Initialize response structure
        formatted_results = {
            "research": {
                "sources": [],
                "key_findings": [],
                "data_points": []
            }
        }

        # Process search results
        if isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    formatted_results["research"]["sources"].append(result.get("url", ""))
                    formatted_results["research"]["key_findings"].append(result.get("content", ""))
                    formatted_results["research"]["data_points"].append({
                        "url": result.get("url", ""),
                        "content": result.get("content", "")
                    })
        logger.info(f"Research completed for query: {query}")
        return json.dumps(formatted_results)
    except Exception as e:
        logger.error(f"Error in financial research for query '{query}': {str(e)}")
        return json.dumps({
            "research": {
                "sources": [],
                "key_findings": [],
                "data_points": []
            }
        })


# Define agents
classifier = Agent(
    role='Query Classifier',
    goal='Categorize user queries to determine if they are financial, portfolio-related, or irrelevant',
    backstory="""You are an expert in analyzing user queries. You excel at distinguishing financial queries (e.g., stock prices, portfolio questions) from greetings (e.g., 'Hello') or general questions (e.g., 'What's the weather?'). Your role is to ensure only relevant financial queries are processed.""",
    verbose=True,
    llm=llm
)

researcher = Agent(
    role='Indian Financial Market Researcher',
    goal='Gather and analyze financial information specific to Indian markets',
    backstory="""You are an expert financial researcher specializing in Indian markets with deep knowledge of SEBI regulations, market dynamics, and financial terminology. You use tools to collect and verify information relevant to Indian investors, avoiding unnecessary searches for straightforward queries.""",
    tools=[financial_research_tool, view_user_portfolio],
    verbose=True,
    llm=llm1
)

advisor = Agent(
    role='Indian Financial Advisor',
    goal='Provide accurate and helpful financial advice for Indian investors',
    backstory="""You are a certified financial advisor with expertise in Indian personal finance, SEBI regulations, tax laws, and market conditions. You analyze research data to deliver clear, actionable advice tailored for Indian investors, ensuring responses are professional and confident.""",
    tools=[view_user_portfolio],
    verbose=True,
    llm=llm1
)

# Classification task with four possible query categories
classify_task = Task(
    description="""
        Analyze the user query to categorize it as one of:
        - 'irrelevant': Queries like greetings or non-financial topics (e.g., "Hi", "Hello", "How is the weather?", etc.).
        - 'conceptual': Financial queries asking for definitions or explanations (e.g., "What is an IPO?", "What is the P/E ratio?", "What do you mean by investment?", "What is the debt/equity ratio?", "What is earnings per share?", etc.).
        - 'real_time': Financial queries that require current data and internet access (e.g., "What is the current stock price?", "Give me the mutual funds with 20% YOY", etc.). Use Gemini directly for this category.
        - 'portfolio': Queries specific to a user's portfolio (e.g., "What's my asset allocation?").

        Query: {query}

        Guidelines:
        - Classify greetings and non-financial questions as 'irrelevant'.
        - Questions asking for definitions or explanations (like those about IPOs, investment, P/E ratio, etc.) are 'conceptual'.
        - Questions requiring current data (like stock prices, mutual funds performance, etc.) are 'real_time' and should be handled by Gemini.
        - Portfolio related queries include any reference to "my portfolio", "asset allocation", or user-specific investments.
        - If ambiguous, lean towards categorizing it as a financial query.

        Return a JSON object:
        {{
            "query_type": "irrelevant|conceptual|real_time|portfolio"
        }}
    """,
    expected_output="A JSON object specifying the query type",
    agent=classifier
)

research_task = Task(
    description="""
        Research the financial query using available tools, focusing on Indian markets.

        Query: {query}
        User ID: {user_id}

        Requirements:
        1. Use the financial_research_tool for market-related queries.
        2. Use view_user_portfolio for portfolio-related queries with user_id={user_id}.
        3. Gather data from Indian financial sources.
        4. Verify information accuracy against Indian market data.
        5. Organize findings by topic.

        Return a JSON object:
        {{
            "research": {{
                "sources": ["Source 1", "Source 2"],
                "key_findings": ["Finding 1", "Finding 2"],
                "data_points": ["Data 1", "Data 2"]
            }}
        }}
    """,
    expected_output="Research findings with sources and data points",
    agent=researcher
)


# advice_task = Task(
#     description="""
#         Provide financial advice based on research findings for Indian markets, tailored to the query type.
#
#         Query: {query}
#         User ID: {user_id}
#         Query Type: {query_type}
#
#         Requirements:
#         1. For 'financial' queries, analyze research findings and provide market-specific advice.
#         2. For 'portfolio' queries, use view_user_portfolio with user_id={user_id} and focus on user-specific advice.
#         3. For 'irrelevant' queries, return a polite rejection in the same JSON format.
#         4. Provide clear, actionable advice for financial/portfolio queries.
#         5. Support recommendations with Indian market data and consider tax/regulatory implications.
#         6. **Important:** If the query requests mutual fund suggestions based on high returns (e.g., "Mutual funds where the gains are 20% YOY"), do NOT provide specific mutual fund names or speculative details. Instead, offer general advice such as considering investments in broader sectors (e.g., small cap or large cap funds) based on prevailing market conditions.
#         7. Be confident and specific in recommendations without disclaimers.
#         8. Use the following JSON structure:
#         {{
#             "advice": {{
#                 "analysis": "Detailed analysis or rejection message",
#                 "recommendations": ["Recommendation 1", "Recommendation 2"],
#                 "supporting_data": ["Data point 1", "Data point 2"],
#                 "sources": ["Source 1", "Source 2"]
#             }}
#         }}
#     """,
#     expected_output="Financial advice or rejection message in JSON format",
#     agent=advisor,
#     context=[research_task]
# )
advice_task = Task(
    description="""
        Provide financial advice based on research findings for Indian markets, tailored to the query type.

        Query: {query}
        User ID: {user_id}
        Query Type: {query_type}

        Requirements:
        1. For 'financial' queries, analyze the research findings and provide market-specific strategic advice.
        2. For 'portfolio' queries, use view_user_portfolio with user_id={user_id} and focus on user-specific suggestions.
        3. For 'irrelevant' queries, return a polite rejection in the same JSON format.
        4. Deliver clear, actionable guidance for both general and portfolio-related financial queries.
        5. Support recommendations with relevant market data and consider local tax and regulatory implications.
        6. When addressing queries that request suggestions based on specific historical high returns or projected performance targets, provide a strategic overview focused on broader market sectors or asset classes rather than naming individual stocks or funds.
        7. Ensure that the advice helps the user understand the risk factors involved and emphasizes a diversified and careful investment approach.
        8. Use the following JSON structure:
        {{
            "advice": {{
                "analysis": "Detailed analysis or rejection message",
                "recommendations": ["General recommendation 1", "General recommendation 2"],
                "supporting_data": ["Data point 1", "Data point 2"],
                "sources": ["Source 1", "Source 2"]
            }}
        }}
    """,
    expected_output="Financial advice or rejection message in JSON format",
    agent=advisor,
    context=[research_task]
)

# Create crews
classification_crew = Crew(
    agents=[classifier],
    tasks=[classify_task],
    verbose=1,
    process=Process.sequential
)

chat_crew = Crew(
    agents=[researcher, advisor],
    tasks=[research_task, advice_task],
    verbose=1,
    process=Process.sequential
)


def _clean_json_response(result_content: str) -> str:
    """
    Clean and extract valid JSON from crew output to ensure parseability.

    Args:
        result_content: Raw output from crew execution.

    Returns:
        A cleaned JSON string.
    """
    logger.debug(f"Cleaning JSON response: {result_content[:100]}...")
    if not result_content.strip().startswith('{'):
        result_content = re.sub(r'```(?:json)?\s*|\s*```', '', result_content)
        json_match = re.search(r'\{.*\}', result_content, re.DOTALL)
        if json_match:
            result_content = json_match.group()

    result_content = result_content.strip()
    try:
        json_obj = json.loads(result_content)
        return json.dumps(json_obj)
    except json.JSONDecodeError as e:
        logger.error(f"JSON cleaning failed: {str(e)}")
        if "Extra data" in str(e):
            position = int(re.search(r'char (\d+)', str(e)).group(1))
            return result_content[:position]
        return result_content


def apply_dynamic_guardrails(chat_response: ChatResponse) -> ChatResponse:
    """
    Dynamically apply guardrails to the ChatResponse.

    This function checks if the response contains disallowed content,
    overly generic disclaimers, foul language, or hate speech, and cleans it up accordingly.
    If the response is empty or too short, it is replaced with a default safe message.
    """
    # Example: If the response is empty or too short, return a safe default.
    if not chat_response.answer or len(chat_response.answer.strip()) < 10:
        logger.warning("Guardrails applied: Response is too short or empty. Returning default safe message.")
        chat_response.answer = "I'm sorry, but I couldn't generate an appropriate response. Please try again later."
        return chat_response

    # Remove or modify disallowed terms.
    disallowed_terms = ["not financial advice", "shit", "speculation"]
    for term in disallowed_terms:
        if term.lower() in chat_response.answer.lower():
            logger.warning("Guardrails applied: Disallowed content detected. Removing sensitive information.")
            # Replace the disallowed term with an empty string.
            chat_response.answer = chat_response.answer.lower().replace(term.lower(), "")

    # Define a list of words/phrases that constitute foul language or hate speech.
    # Note: This list is a sample and should be expanded based on your requirements.
    offensive_terms = [
        "shit",  # replace with actual offensive terms
    ]

    # Replace offensive words or phrases with a neutral placeholder.
    for word in offensive_terms:
        # Check in a case-insensitive manner.
        if word.lower() in chat_response.answer.lower():
            logger.warning(f"Guardrails applied: Offensive term '{word}' detected. Censoring content.")
            # Replace all occurrences (regardless of case) with '[censored]'
            # Here, we perform a simple case-insensitive replacement.
            # For more nuanced filtering, consider using regular expressions.
            chat_response.answer = chat_response.answer.replace(word, "[censored]")
            chat_response.answer = chat_response.answer.replace(word.capitalize(), "[censored]")
            chat_response.answer = chat_response.answer.replace(word.upper(), "[censored]")

    # Additional dynamic checks can be inserted here.
    return chat_response


async def get_financial_advice(query: str, user_id: Optional[int] = None) -> ChatResponse:
    """
    Process a user query to provide financial advice or reject irrelevant queries,
    and apply dynamic guardrails to the final output.

    Args:
        query: The user's input query.
        user_id: Optional user ID for portfolio-related queries.

    Returns:
        A ChatResponse object with advice or an error/rejection message.
    """
    logger.info(f"Processing query: '{query}' for user_id: {user_id}")
    loop = None
    try:
        # Step 1: Classify the query
        logger.debug("Running query classification")
        classification_result = classification_crew.kickoff(inputs={'query': query})
        try:
            # Extract query type from classification output
            classification_content = (
                classification_result.tasks[-1].output
                if hasattr(classification_result, 'tasks') and classification_result.tasks
                else str(classification_result)
            )
            cleaned_classification = _clean_json_response(classification_content)
            query_type = json.loads(cleaned_classification).get('query_type', 'financial')
            logger.info(f"Query classified as: {query_type}")
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Classification parsing failed: {str(e)}. Defaulting to 'financial'")
            query_type = 'financial'

        # Step 2: Handle irrelevant queries immediately
        if query_type == 'irrelevant':
            logger.info("Query is irrelevant; returning rejection response")
            chat_response = ChatResponse(
                answer="I'm a financial analyst and can only assist with financial queries.",
                recommendations=[],
                supporting_data=[],
                sources=[],
                timestamp=datetime.now()
            )
            return apply_dynamic_guardrails(chat_response)

        # Step 2.1: Handle conceptual queries via Gemini
        if query_type == 'conceptual':
            if GENAI_AVAILABLE:
                logger.info("Query is conceptual; generating response using Gemini (simulated streaming)")
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(query)
                full_text = response.text

                # Simulate streaming
                chunk_size = 50
                final_text = ""
                for i in range(0, len(full_text), chunk_size):
                    chunk = full_text[i:i + chunk_size]
                    final_text += chunk
                    print(chunk, end='', flush=True)
                    await asyncio.sleep(0.1)

                return ChatResponse(
                    answer=final_text,
                    recommendations=[],
                    supporting_data=[],
                    sources=[],
                    timestamp=datetime.now()
                )
            else:
                logger.warning("Gemini not available; cannot process conceptual query")
                return ChatResponse(
                    answer="I'm sorry, but I cannot process conceptual queries at the moment.",
                    recommendations=[],
                    supporting_data=[],
                    sources=[],
                    timestamp=datetime.now()
                )

        # Queries that require real-time data and any other financial queries (e.g., portfolio)
        # will be processed through the standard crew flow.

        # Step 3: Prepare inputs for financial/portfolio queries
        inputs = {
            'query': query,
            'user_id': user_id,
            'query_type': query_type
        }
        logger.debug(f"Prepared inputs: {inputs}")

        # Step 4: Fetch portfolio data if user_id is provided
        if user_id:
            try:
                db = next(get_db())
                portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
                if portfolio:
                    portfolio_data = {
                        "asset_allocation": json.loads(portfolio.portfolio_json).get('asset_allocation', {}),
                        "risk_assessment": json.loads(portfolio.portfolio_json).get('risk_analysis', {}),
                        "performance_projection": json.loads(portfolio.portfolio_json).get('performance_projection', {})
                    }
                    inputs['portfolio_data'] = json.dumps(portfolio_data)
                    logger.info(f"Portfolio data added for user_id: {user_id}")
            except Exception as e:
                logger.error(f"Error fetching portfolio data: {str(e)}")

        # Step 5: Execute the chat crew for 'real_time' and all other financial queries
        logger.debug("Starting chat crew execution")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = chat_crew.kickoff(inputs=inputs)
            # Extract output from the last task (advice_task)
            if hasattr(result, 'tasks') and result.tasks:
                result_content = result.tasks[-1].output
            else:
                result_content = str(result)
                logger.warning("No tasks found in result; using stringified output")

            # Clean and parse the response
            cleaned_json = _clean_json_response(result_content)
            try:
                advice_data = json.loads(cleaned_json)
                advice = advice_data.get('advice', {})
                logger.info("Advice generated successfully")
                chat_response = ChatResponse(
                    answer=advice.get('analysis', 'No advice available'),
                    recommendations=advice.get('recommendations', []),
                    supporting_data=advice.get('supporting_data', []),
                    sources=advice.get('sources', []),
                    timestamp=datetime.now()
                )
                return apply_dynamic_guardrails(chat_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {str(e)}. Raw: {result_content}")
                chat_response = ChatResponse(
                    answer="I apologize, but I'm having trouble processing your request. Please try again.",
                    recommendations=[],
                    supporting_data=[],
                    sources=[],
                    timestamp=datetime.now()
                )
                return apply_dynamic_guardrails(chat_response)

        finally:
            if loop:
                loop.close()
                logger.debug("Event loop closed")

    except Exception as e:
        logger.error(f"Unexpected error in get_financial_advice: {str(e)}")
        chat_response = ChatResponse(
            answer="I apologize, but I'm having trouble processing your request. Please try again.",
            recommendations=[],
            supporting_data=[],
            sources=[],
            timestamp=datetime.now()
        )
        return apply_dynamic_guardrails(chat_response)



