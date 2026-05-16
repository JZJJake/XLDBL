import os
import re

translations = {
    r'help="Specify the target directory for the wiki"': r'help="指定wiki的目标目录"',
    r'help="A description of the domain or purpose of the wiki"': r'help="wiki领域或用途的描述"',
    r'help="Clear the default wiki setting"': r'help="清除默认的wiki设置"',
    r'help="Print verbose debug output"': r'help="打印详细的调试输出"',
    r'help="The wiki to query"': r'help="要查询的wiki"',
    r'help="Target wiki"': r'help="目标wiki"',
    r'help="Wiki to query"': r'help="要查询的wiki"',
    r'help="List pending and failed jobs"': r'help="列出待处理和失败的任务"',
    r'help="Ingest a document or web page"': r'help="提取文档或网页"',
    r'help="File path or URL"': r'help="文件路径或URL"',
    r'help="Start the background worker"': r'help="启动后台工作进程"',
    r'help="Start the wiki engine"': r'help="启动wiki引擎"',
    r'help="Target wiki \(if not set as default\)"': r'help="目标wiki（如果没有设置为默认）"',
    r'help="Force ingestion even if cached"': r'help="强制提取，即使已缓存"',
    r'help="Run the server in the background"': r'help="在后台运行服务器"',
    r'help="Port to run the HTTP server on"': r'help="运行HTTP服务器的端口"',
    r'help="Uninstall a wiki"': r'help="卸载wiki"',
    r'help="Bypass confirmation"': r'help="绕过确认"',
    r'help="Set the default wiki"': r'help="设置默认wiki"',
    r'help="Initialise a new wiki"': r'help="初始化新的wiki"',
    r'help="Query the wiki"': r'help="查询wiki"',
    r'help="Generate an offline CLI response"': r'help="生成离线CLI响应"',
    r'help="Generate a RAG-style answer"': r'help="生成RAG风格的答案"',
    r'help="Batch ingest all documents in a directory"': r'help="批量提取目录中的所有文档"',
    r'help="Ingest URLs from a text file"': r'help="从文本文件中提取URL"',
    r'help="Just analyse, do not write pages"': r'help="仅分析，不写入页面"',
    r'help="Max sub-searches per query"': r'help="每个查询的最大子搜索数"',
    r'help="Skip staging and write directly to wiki/"': r'help="跳过暂存，直接写入wiki/"',
    r'help="Target wiki \(if not default\)"': r'help="目标wiki（如果不是默认）"',
    r'help="Only lint this slug"': r'help="仅检查此页面标识符"',
    r'help="Auto-resolve high confidence lint hits"': r'help="自动解决高可信度的检查问题"',
    r'help="Include contradictions in lint"': r'help="在检查中包括矛盾"',
    r'help="Include orphans in lint"': r'help="在检查中包括孤立页面"',
    r'help="Lint specific scopes only"': r'help="仅检查特定范围"',
    r'help="Filter jobs by status"': r'help="按状态过滤任务"',
    r'help="Retry a dead job"': r'help="重试死任务"',
    r'help="The ID of the job to retry"': r'help="要重试的任务ID"',
    r'help="Remove dead/completed jobs"': r'help="删除死任务/已完成的任务"',
    r'help="Keep jobs newer than N days"': r'help="保留N天内的新任务"',
    r'help="The wiki to scaffold"': r'help="要构建脚手架的wiki"',
    r'help="Regenerate AGENTS.md"': r'help="重新生成AGENTS.md"',
    r'help="Regenerate index.md"': r'help="重新生成index.md"',
    r'help="Regenerate purpose.md"': r'help="重新生成purpose.md"',
    r'help="Build a context pack"': r'help="构建上下文包"',
    r'help="Token budget for the context pack"': r'help="上下文包的Token预算"',
    r'help="Save output to file"': r'help="将输出保存到文件"',
    r'help="List candidate pages"': r'help="列出候选页面"',
    r'help="Promote a candidate page"': r'help="提升候选页面"',
    r'help="The slug of the candidate to promote"': r'help="要提升的候选页面的标识符"',
    r'help="Promote all candidates"': r'help="提升所有候选页面"',
    r'help="Discard a candidate page"': r'help="丢弃候选页面"',
    r'help="The slug of the candidate to discard"': r'help="要丢弃的候选页面的标识符"',
    r'help="Discard all candidates"': r'help="丢弃所有候选页面"',
    r'help="Set staging policy"': r'help="设置暂存策略"',
    r'help="Route all pages to candidates/"': r'help="将所有页面路由到candidates/"',
    r'help="Route high-confidence to wiki/, rest to candidates/"': r'help="高可信度路由到wiki/，其余路由到candidates/"',
    r'help="Route directly to wiki/"': r'help="直接路由到wiki/"',
    r'help="Minimum confidence to promote"': r'help="提升的最小可信度"',
    r'help="Show recent cost events"': r'help="显示最近的成本事件"',
    r'help="Number of days to look back"': r'help="要回顾的天数"',
    r'help="Output as JSON"': r'help="作为JSON输出"',
    r'help="Show recent audit history"': r'help="显示最近的审计历史"',
    r'help="Number of events to show"': r'help="要显示的事件数"',
    r'help="Show recent system events"': r'help="显示最近的系统事件"',
    r'help="List scheduled ops"': r'help="列出计划的操作"',
    r'help="Add a scheduled op"': r'help="添加计划的操作"',
    r'help="The CLI command to run \(e.g. \"lint run\"\)"': r'help="要运行的CLI命令（例如 \"lint run\"）"',
    r'help="Cron expression \(e.g. \"0 3 \* \* \*\"\)"': r'help="Cron表达式（例如 \"0 3 * * *\"）"',
    r'help="Remove a scheduled op"': r'help="删除计划的操作"',
    r'help="The ID of the op to remove"': r'help="要删除的操作的ID"',
    r'help="List available demos"': r'help="列出可用的演示"',
    r'help="Install a demo wiki"': r'help="安装演示wiki"',
    r'help="The name of the demo to install"': r'help="要安装的演示的名称"',
    r'help="Path to Obsidian vault"': r'help="Obsidian vault的路径"',
    r'help="Re-register Obsidian plugin"': r'help="重新注册Obsidian插件"',
    r'help="Generate ROUTING.md from index.md"': r'help="从index.md生成ROUTING.md"',
    r'help="Clean up invalid routing entries"': r'help="清理无效的路由条目"',
    r'help="Check ROUTING.md against actual files"': r'help="检查ROUTING.md与实际文件是否匹配"',
}

for root, _, files in os.walk('synthadoc/cli'):
    for f in files:
        if f.endswith('.py'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
            for en, zh in translations.items():
                content = re.sub(en, zh, content)

            # Simple click.echo translations
            content = content.replace('click.echo("Cache cleared', 'click.echo("缓存已清除')
            content = content.replace('click.echo("No active wiki set', 'click.echo("未设置活动的wiki')
            content = content.replace('click.echo("Server is running on', 'click.echo("服务器运行在')
            content = content.replace('click.echo("Press Ctrl+C to stop', 'click.echo("按Ctrl+C停止')
            content = re.sub(r'click\.echo\("Job ([^ ]+) queued', r'click.echo("任务 \1 已加入队列', content)
            content = content.replace('click.echo("Job cancelled', 'click.echo("任务已取消')
            content = content.replace('click.echo("Failed to', 'click.echo("失败：')
            content = content.replace('click.echo("Success', 'click.echo("成功')
            content = content.replace('click.echo("Error:', 'click.echo("错误：')
            content = content.replace('click.echo("Warning:', 'click.echo("警告：')
            content = content.replace('click.echo("Done', 'click.echo("完成')

            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write(content)

print("done")
