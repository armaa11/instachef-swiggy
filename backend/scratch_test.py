import asyncio
from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(
      base_url = "https://integrate.api.nvidia.com/v1",
      api_key = "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"
    )

    completion = await client.chat.completions.create(
      model="nvidia/nemotron-3-super-120b-a12b",
      messages=[{"role":"user","content":"Hi, just say Hello in JSON: {\"message\": \"Hello\"}"}],
      temperature=1,
      top_p=0.95,
      max_tokens=16384,
      extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":16384},
      stream=True
    )

    output = ""
    async for chunk in completion:
      if not chunk.choices:
        continue
      if chunk.choices[0].delta.content is not None:
        output += chunk.choices[0].delta.content

    print("FINAL OUTPUT:", output)

asyncio.run(main())
