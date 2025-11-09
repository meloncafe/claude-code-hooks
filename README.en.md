# Claude Code Hooks

Having used Claude Code since its API days and now on the Max 2x plan while working on a fairly large-scale project, I've tried various approaches to “consume tokens wisely, even when consuming them.” Since I'll likely continue using this method through this year, I wanted to share it.

I've been developing for over 10 years. While I'm not a developer by profession now and only use it for personal side projects, I've spent about $2000 this year on Anthropic and other LLMs and want to share my results.

## 1. Claude Code Needs Restrictions

Claude Code is excellent in most situations.

However, when working on various package modules, backends, frontends, etc., within a massive monorepo, Claude starts to get confused.

More precisely, in this vast space, it becomes highly confusing about which project is currently active, which project was worked on in the previous session, and the usage for tests or each specific module.

Working on a single project, separating into microservices, connecting only one Claude Code per project

These methods might be slightly more efficient and minimize Claude's confusion, but after trying them all, I concluded that Claude itself needs limitations or guidelines.

## 2. Claude Code reads CLAUDE.md

When you first run Claude Code in a project, it outputs a message recommending you create a project-specific instruction file called CLAUDE.md using the /init command.

Like most Claude users, you've probably created a CLAUDE.md file and added various project-specific instructions.

However, if you only use Claude Code within a single session—meaning one conversation—and then stop, there's generally no major issue. But if you continue working by connecting to a previous session, due to features like Auto Compact (which Anthropic heavily promotes) for automatic context compression, or due to Claude Code CLI memory issues causing it to restart after closing, Claude Code begins to ignore CLAUDE.md.

This situation becomes particularly severe after Auto Compact occurs; post-Auto Compact, it won't even reference the content written in CLAUDE.md.

While it summarizes the previous session's content and passes it as a prompt to the next session, it literally fails to properly convey the instructions being followed, any limitations set during that session, or any user interventions and subsequent instructions given midway.

Therefore, if Auto Compact occurs immediately after finishing a code task and moves to the next session, Claude in that session will often make the very foolish mistake of “interpreting on its own” based solely on the prompt carried over from the previous session. It will then delete the already completed code, claiming it's incorrect, or start the task over from the beginning.

## 3. Hook functionality depends entirely on how you use it

While using Claude Code, I find myself wondering why I only started using the Hook feature now.

Guidelines entered in Markdown can instruct Claude, but whether it follows them is entirely up to Claude.

However, Hooks can create “enforceability” for Claude Code.

They can be used in many ways, but examples include the following:

1. Command restrictions
2. Token restrictions
3. Pattern restrictions
4. Restrictions on incorrect behavior
5. Instructions on what to prioritize when a session starts

Beyond these, various combinations are possible. When I used them, they were extremely useful and significantly curbed Claude's tendency to run wild.

The hooks I currently use are listed below.

```
auto_compact.py
command_restrictor.py
context_recovery_helper.py
detect_session_finish.py
no_mock_code.py
pattern_enforcer.py
post_session_hook.py
post_tool_use_compact_progress.py
pre_session_hook.py
secret_scanner.py
session_start.py
timestamp_validator.py
token_manager.py
validate_git_commit.py
```

To explain, 

1. Whether starting a new session or entering via Auto Compact from a previous session, session_start or pre_session_hook displays a summary of the previous session.
    
    (Details about the summary will be covered below.)
    
2. Every command executed by Claude must first pass through command_restrictor.
This restricts most incorrect command inputs.
3. It checks the current token usage.
If you want to limit the number of tokens used, this part enforces the limit and halts the task.
4. Once a task is completed or code is modified, scripts like secret_scanner and no_mock_code perform basic security checks and inspect items marked as TODO but not yet implemented.
Claude may claim to have implemented something, but many TODO items remain unimplemented.
This forces the implementation of those parts.
5. If Auto Commit is enabled in Hook settings or Claude itself offers to perform a Git commit, commit messages like “by Claude” can end up messy without the developer's knowledge.
Therefore, if Claude attempts a git commit, it must pass validate_git_commit.
This ensures clean commit messages by restricting invalid formats or unnecessary phrases like “Co-Auth.”

The most useful aspects of the current Hook configuration are command restrictions and providing a clear summary of the previous session during Auto Compact.

The automatic context backup and summary provision for the next session follow a simple flow as described below.

Claude Auto Compact triggers → PreCompactHook executes → Hook script backs up current context file (JSONL file provided by Claude) → Initial refinement of unnecessary parts from the backup (reducing approx. 7-8Mb to 100-200Kb) → Using the refined content, generate a summary via Claude Haiku 4.5 model using Claude Code CLI → Display the summarized content at the start of the next session and notify Claude about what was done in the previous session and what needs to be done next

Writing it out, it's not exactly simple.

The key point is that by taking the current context source, extracting only the necessary parts, requesting Claude to generate a summary, and then providing that summary at the start of the next session (e.g., via PreSession), we can proceed with longer tasks more reliably. I'm satisfied with this approach.

Command constraints are also useful for monitoring all commands generated by Claude Code, preventing unauthorized commands, or controlling commands that can't be managed via curl or Claude Code's permission features.

For example, even if curl is set to Allow in Claude Code Settings, it still asks for permission every single time it's used.

This is extremely bothersome and frustrating. While I might not have found other methods, most approaches I tried weren't useful for me.

The command restriction script allows clear differentiation between Allow/Deny/Ask. Even if a specific command is permitted, it can be set to Ask for user confirmation. Commands that require permission every time can be automatically set to Allow.
 

(For example, even if `rm -rf` is set to Allow, using this script will prompt the user to confirm usage.)

## 4. Skills must be used with Hooks

The recently released Claude Skills offer various capabilities.

The traditional Agent approach required the hassle of explicitly invoking the Agent. Skills, however, are like Claude saying, “Hey, I can use this skill!” Properly configured, they prevent scenarios where the [CLAUDE.md](http://CLAUDE.md) file exceeds 3000 lines.

However, Skills aren't a panacea.

These are “guidelines” for using the feature properly, but whether Claude actually follows them is up to Claude.

Therefore, even if you create and possess various technologies like backend, frontend, API, etc., using Skills, they're useless if you can't properly control them.

## 5. Set up a project-specific CLI whenever possible

Most of my projects are Python-based, and lately, I've been working a lot with FastAPI + React.

Speaking specifically for Python/FastAPI, I recommend using the Typer/Rich library to build a CLI that can be used within your project.

During development, you have to handle many tasks.

You need to manage databases, manage API specifications, and when testing, you often have to manually create test accounts, apply permissions, check the currently running backend or frontend, and perform various other manual tasks.

First, use Claude Code to build a CLI that can handle these manual tasks.

Especially when you need to directly access and modify the database or execute queries, Claude will almost always attempt to use the database's CLI for access. It will repeatedly ask for the login credentials, and even if provided, it often fails to perform the task correctly.

By creating a dedicated CLI for these tasks and teaching Claude how to use it, you save significant time. Claude won't waste time trying various approaches haphazardly; it will simply use the CLI to perform the necessary operations.

Of course, this CLI is not for production use. A separate production-ready CLI must be configured; this setup is purely for development purposes.

## 6. Auxiliary Storage is Essential

Claude is not omnipotent.

At the start of each new session, it will ask like a new employee: what happened in the session, when this code was modified, and how modifications were attempted.

To mitigate this as much as possible, there are many auxiliary memory solutions available for Claude, including open-source memory and subscription-based memory.

I use ChromaDB. I've tried other expensive, supposedly good options like Qdrant, Mem0, and Pinecore before, but I still find ChromaDB sufficient.

However, I wanted identical memory across work, home, and mobile. While I could have used Chroma Cloud, I preferred to keep sensitive parts under my own management. So I started a separate project and recently began deploying it.

Of course, even if you connect ChromaDB, there's no guarantee Claude will use it, so you need to enforce it.

This applies to other memory solutions as well.

## 7. Sentry occasionally helps

Claude only checks logs when explicitly told to “look at them.”

But even then, it consistently treats the log folder differently per session. If the logs aren't where that session's Claude expects them, it deems “no logs exist” and starts making assumptions and modifications on its own.

Of course, if you tell it the log folder and ask it to check the last log, it finds the issue over 90% of the time.

However, based on my continued use, log files inevitably keep growing, leading to significant waste of unnecessary tokens.

This is where Sentry proves useful.

Sentry holds the full backtrace for the error, enabling analysis of only the necessary parts.

However, even if you tell Claude to use Sentry, it won't enforce it. If there are multiple projects, Claude won't even bother looking for the project and will just spit out “Cannot find” and proceed with guesswork.

## 8. Claude's Think Function Is Unpredictable

Claude Code has a standard mode and a Think mode.

Think mode acts as an intermediate guide, allowing Claude to think for itself, judge which direction is best, and proceed accordingly.

However, this feature isn't perfect either.

Sometimes it gets too absorbed in its own thoughts or throws around wild, speculative theories, producing nonsensical results.

For users who have to spend extra tokens to use the Think feature, it's enough to make your head spin.

Therefore, unless you're a heavy user like Max Plan, I recommend working mostly in Normal mode and only using Think for highly complex tasks requiring deep project-wide understanding.

## Conclusion

I hope this content offers some assistance to those coding using Claude or other AI LLMs.

The Claude Hook, Skills, CLI, and Memory samples mentioned in the article are available below. Since they're based on my project, you may need to make some adjustments for your own projects.

I'm currently developing and refining Hooks, so this repository will likely continue to be updated.

I've wanted to release this for a while, but various hassles and doubts about actual users made me delay. Now that the code has evolved to a point I'm reasonably satisfied with, I'm releasing it.

I've spent a lot on Anthropic this year, and only now do I feel like I'm using it properly. I'm sharing the content and distributing the code, hoping it might help a little with your wallets.

Feel free to submit PRs or open issues for questions about hook usage or improvements.

(This document, code was originally written in Korean. The English translation is by DeepL and may not fully convey my intended meaning.)

ChromaDB Remote MCP Server : https://github.com/meloncafe/chromadb-remote-mcp

Claude Hooks : https://github.com/meloncafe/claude-code-hooks