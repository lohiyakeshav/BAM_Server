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
# # Load environment variables
# load_dotenv()
#
# # Initialize LLM
# llm = LLM(
#     model='gemini/gemini-2.0-flash',
#     api_key=os.getenv("GEMINI_API_KEY")
# )
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
#     llm=llm
# )
#
# advisor = Agent(
#     role='Indian Financial Advisor',
#     goal='Provide accurate and helpful financial advice for Indian investors',
#     backstory="""You are a certified financial advisor with expertise in Indian personal finance, SEBI regulations, tax laws, and market conditions. You analyze research data to deliver clear, actionable advice tailored for Indian investors, ensuring responses are professional and confident.""",
#     tools=[view_user_portfolio],
#     verbose=True,
#     llm=llm
# )
#
# # Define tasks
# classify_task = Task(
#     description="""
#         Analyze the user query to categorize it as one of:
#         - 'financial': Queries about stocks, markets, investments, or requiring research (e.g., 'What are Reliance stock prices?').
#         - 'portfolio': Queries about the user's portfolio (e.g., 'What's my asset allocation?').
#         - 'irrelevant': Greetings or non-financial questions (e.g., 'Hello', 'What's the weather?').
#
#         Query: {query}
#
#         Guidelines:
#         - Financial queries often mention stocks, mutual funds, market trends, or economic terms.
#         - Portfolio queries reference 'my portfolio', 'asset allocation', or user-specific investments.
#         - Irrelevant queries include greetings, weather, or unrelated topics.
#         - If ambiguous, lean toward 'financial' to avoid missing valid queries.
#
#         Return a JSON object:
#         {{
#             "query_type": "financial|portfolio|irrelevant"
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
# def _clean_json_response(result_content: str) -> str:
#     """
#     Clean and extract valid JSON from crew output to ensure parseability.
#
#     Args:
#         result_content: Raw output from crew execution.
#
#     Returns:
#         A cleaned JSON string.
#     """
#     logger.debug(f"Cleaning JSON response: {result_content[:100]}...")
#     if not result_content.strip().startswith('{'):
#         result_content = re.sub(r'```(?:json)?\s*|\s*```', '', result_content)
#         json_match = re.search(r'\{.*\}', result_content, re.DOTALL)
#         if json_match:
#             result_content = json_match.group()
#
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
# async def get_financial_advice(query: str, user_id: Optional[int] = None) -> ChatResponse:
#     """
#     Process a user query to provide financial advice or reject irrelevant queries.
#
#     Args:
#         query: The user's input query.
#         user_id: Optional user ID for portfolio-related queries.
#
#     Returns:
#         A ChatResponse object with advice or an error/rejection message.
#     """
#     logger.info(f"Processing query: '{query}' for user_id: {user_id}")
#     loop = None
#     try:
#         # Step 1: Classify the query
#         logger.debug("Running query classification")
#         classification_result = classification_crew.kickoff(inputs={'query': query})
#         try:
#             # Extract query type from classification output
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
#         # Step 2: Handle irrelevant queries early
#         # if query_type == 'irrelevant':
#         #     logger.info("Query is irrelevant; returning rejection response")
#         #     return ChatResponse(
#         #         answer="I'm a financial analyst and can only assist with financial queries.",
#         #         recommendations=[],
#         #         supporting_data=[],
#         #         sources=[],
#         #         timestamp=datetime.now()
#         #     )
#         #     logger.error(f"JSON parsing failed: {str(e)}. Raw: {result_content}")
#         #
#         if query_type == 'irrelevant':
#             logger.info("Query is irrelevant; generating response using Gemini")
#             from google import genai
#             gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
#             response = gemini_client.models.generate_content(
#                 model="gemini-2.0-flash",
#                 contents=query
#             )
#             return ChatResponse(
#                 answer=response.text,
#                 recommendations=[],
#                 supporting_data=[],
#                 sources=[],
#                 timestamp=datetime.now()
#             )
#
#         # Step 3: Prepare inputs for financial/portfolio queries
#         inputs = {
#             'query': query,
#             'user_id': user_id,
#             'query_type': query_type
#         }
#         logger.debug(f"Prepared inputs: {inputs}")
#
#         # Step 4: Fetch portfolio data if user_id is provided
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
#         # Step 5: Execute the chat crew
#         logger.debug("Starting chat crew execution")
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         try:
#             result = chat_crew.kickoff(inputs=inputs)
#             # Extract output from the last task (advice_task)
#             if hasattr(result, 'tasks') and result.tasks:
#                 result_content = result.tasks[-1].output
#             else:
#                 result_content = str(result)
#                 logger.warning("No tasks found in result; using stringified output")
#
#             # Clean and parse the response
#             cleaned_json = _clean_json_response(result_content)
#             try:
#                 advice_data = json.loads(cleaned_json)
#                 advice = advice_data.get('advice', {})
#                 logger.info("Advice generated successfully")
#                 return ChatResponse(
#                     answer=advice.get('analysis', 'No advice available'),
#                     recommendations=advice.get('recommendations', []),
#                     supporting_data=advice.get('supporting_data', []),
#                     sources=advice.get('sources', []),
#                     timestamp=datetime.now()
#                 )
#             except json.JSONDecodeError as e:
#                 logger.error(f"JSON parsing failed: {str(e)}. Raw: {result_content}")
#                 return ChatResponse(
#                     answer="I apologize, but I'm having trouble processing your request. Please try again.",
#                     recommendations=[],
#                     supporting_data=[],
#                     sources=[],
#                     timestamp=datetime.now()
#                 )
#
#         finally:
#             if loop:
#                 loop.close()
#                 logger.debug("Event loop closed")
#
#     except Exception as e:
#         logger.error(f"Unexpected error in get_financial_advice: {str(e)}")
#         return ChatResponse(
#             answer="I apologize, but I'm having trouble processing your request. Please try again.",
#             recommendations=[],
#             supporting_data=[],
#             sources=[],
#             timestamp=datetime.now()
#         )




#### Working code




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

# Initialize LLM for the agents using OpenAI ChatGPT
llm = LLM(
    model='openai/gpt-3.5-turbo',
    api_key=os.getenv("OPENAI_API_KEY")
)
llm1 = LLM(
    model='gemini/gemini-2.0-flash',
    api_key=os.getenv("GEMINI_API_KEY")
)
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

advice_task = Task(
    description="""
        Provide financial advice based on research findings for Indian markets, tailored to the query type.

        Query: {query}
        User ID: {user_id}
        Query Type: {query_type}

        Requirements:
        1. For 'financial' queries, analyze research findings and provide market-specific advice.
        2. For 'portfolio' queries, use view_user_portfolio with user_id={user_id} and focus on user-specific advice.
        3. For 'irrelevant' queries, return a polite rejection in the same JSON format.
        4. Provide clear, actionable advice for financial/portfolio queries.
        5. Support recommendations with Indian market data and consider tax/regulatory implications.
        6. Be confident and specific in recommendations without disclaimers.
        7. Use the following JSON structure:
        {{
            "advice": {{
                "analysis": "Detailed analysis or rejection message",
                "recommendations": ["Recommendation 1", "Recommendation 2"],
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



async def get_financial_advice(query: str, user_id: Optional[int] = None) -> ChatResponse:
    """
    Process a user query to provide financial advice or reject irrelevant queries.

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
            return ChatResponse(
                answer="I'm a financial analyst and can only assist with financial queries.",
                recommendations=[],
                supporting_data=[],
                sources=[],
                timestamp=datetime.now()
            )

        # Step 2.1: Handle conceptual queries via Gemini
        if query_type == 'conceptual':
            logger.info("Query is conceptual; generating response using Gemini")
            from google import genai
            gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=query
            )
            return ChatResponse(
                answer=response.text,
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
                return ChatResponse(
                    answer=advice.get('analysis', 'No advice available'),
                    recommendations=advice.get('recommendations', []),
                    supporting_data=advice.get('supporting_data', []),
                    sources=advice.get('sources', []),
                    timestamp=datetime.now()
                )
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {str(e)}. Raw: {result_content}")
                return ChatResponse(
                    answer="I apologize, but I'm having trouble processing your request. Please try again.",
                    recommendations=[],
                    supporting_data=[],
                    sources=[],
                    timestamp=datetime.now()
                )

        finally:
            if loop:
                loop.close()
                logger.debug("Event loop closed")

    except Exception as e:
        logger.error(f"Unexpected error in get_financial_advice: {str(e)}")
        return ChatResponse(
            answer="I apologize, but I'm having trouble processing your request. Please try again.",
            recommendations=[],
            supporting_data=[],
            sources=[],
            timestamp=datetime.now()
        )
