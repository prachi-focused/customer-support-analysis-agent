from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

message = [HumanMessage(content="What is the capital of France?", role="user")]

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

response = model.invoke(message)

print(response.content)