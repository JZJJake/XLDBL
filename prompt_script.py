import sys
content = ""
with open("synthadoc/cli/main.py", "r", encoding="utf-8") as f:
    content = f.read()

injection = """
    import os
    if not os.environ.get("DEEPSEEK_API_KEY"):
        api_key = click.prompt("请输入DeepSeek API Key (DEEPSEEK_API_KEY)", type=str, hide_input=True)
        os.environ["DEEPSEEK_API_KEY"] = api_key
"""
content = content.replace('def cli(ctx, verbose):\n    """Domain-agnostic LLM wiki engine"""', 'def cli(ctx, verbose):\n    """Domain-agnostic LLM wiki engine"""' + injection)

with open("synthadoc/cli/main.py", "w", encoding="utf-8") as f:
    f.write(content)
