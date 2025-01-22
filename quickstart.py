from openai import AzureOpenAI
from dotenv import dotenv_values

get_env = dotenv_values(".env") 

model=get_env["AZURE_OPENAI_MODEL"]


client = AzureOpenAI(
  azure_endpoint = get_env["AZURE_OPENAI_ENDPOINT"], 
  api_key=get_env["AZURE_OPENAI_API_KEY"],  
  api_version=get_env["AZURE_OPENAI_VERSION"]
)



response = client.chat.completions.create(
    model=model, # model = "deployment_name".
    messages=[
        # {"role": "system", "content": "You are a helpful assistant."},
        # {"role": "user", "content": "Does Azure OpenAI support customer managed keys?"},
        # {"role": "assistant", "content": "Yes, customer managed keys are supported by Azure OpenAI."},
        # {"role": "user", "content": "Do other Azure AI services support this too?"}

        {"role": "user", "content": "tell me about the old Ghana empire"},
    ]
)

print(response.choices[0].message.content)