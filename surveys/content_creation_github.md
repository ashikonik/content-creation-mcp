# GitHub survey — content creation skills, agents, and tools

This survey drove the corpus in `skills/` and `agents/`. It swept GitHub for repositories that help create content — video, images, audio, text, 3D, and design — in two passes:

* **List A** — repositories containing agent or skill definitions: `SKILL.md` files, `agents/` directories, or MCP servers.
* **List B** — repositories that are content-generation tools or libraries in their own right.

**43,362 repositories** classified in total (12,730 in list A, 30,632 in list B). Both lists are sorted by stars, descending.

## Star distribution

| Threshold | List A | List B |
|---|---|---|
| >=100 stars | 1,012 | 4,289 |
| >=500 stars | 441 | 1,896 |
| >=1000 stars | 304 | 1,148 |
| >=10000 stars | 61 | 174 |
| >=50000 stars | 13 | 27 |

## Modality split

| Modality | List A | List B |
|---|---|---|
| 3d | 620 | 1,242 |
| audio | 1,710 | 7,368 |
| avpipe | 257 | 292 |
| design | 1,422 | 2,260 |
| image | 2,319 | 5,814 |
| text | 2,348 | 2,713 |
| video | 4,054 | 10,943 |

## Top repositories — list A (agent/skill definitions)

| Stars | Repository | Description |
|---:|---|---|
| 160,465 | [langgenius/dify](https://github.com/langgenius/dify) | Build Agentic workflows, RAG pipelines, with rich AI model and tool support on one collaborative workspace. De… |
| 110,457 | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Agent skills that give coding agents taste: art direction, reference images and a browser check instead of gen… |
| 109,087 | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | Give your AI agent eyes to see the entire internet. Read & search Twitter, Reddit, YouTube, GitHub, Bilibili, … |
| 103,585 | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | The design vocabulary for your coding agent. Steer with polish and bolder, review with critique and audit, cat… |
| 93,763 | [tt-a1i/archify](https://github.com/tt-a1i/archify) | Turn any idea, plan, or codebase into a beautiful interactive diagram. An agent skill for Claude Code, Codex, … |
| 79,354 | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | Write HTML. Render video. Built for agents. |
| 76,952 | [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | World's first open-source, agentic video production system. 12 production pipelines, 100+ tools, 700+ agent sk… |
| 66,700 | [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | AI agent skill that researches any topic across Reddit, X, YouTube, HN, Polymarket, and the web - then synthes… |
| 65,229 | [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) | Editorial diagram design for Claude Code, Codex, GitHub Copilot, Cursor, Factory Droid, Qoder, and Pi. 45 diag… |
| 65,145 | [blader/humanizer](https://github.com/blader/humanizer) | Agent skill that removes signs of AI-generated writing from text |
| 58,654 | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | Marketing skills for Claude Code and AI agents. CRO, copywriting, SEO, analytics, and growth engineering. |
| 55,474 | [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | Academic Research Skills for Claude Code: research → write → review → revise → finalize |
| 50,801 | [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | Agent skills for Obsidian. Teach your agent to use Obsidian CLI and open formats including Markdown, Bases, JS… |
| 48,503 | [Nutlope/hallmark](https://github.com/Nutlope/hallmark) | Anti-AI-slop design skill for Claude Code, Cursor, and Codex. |
| 46,770 | [LibreChat-AI/LibreChat](https://github.com/LibreChat-AI/LibreChat) | Enhanced ChatGPT Clone: Features Agents, MCP, Skills, DeepSeek, Anthropic, AWS, OpenAI, Responses API, Azure, … |
| 42,230 | [wshobson/agents](https://github.com/wshobson/agents) | Plugins, agents, skills, and commands for Claude Code, Codex CLI, Cursor, OpenCode, Antigravity CLI, GitHub Co… |
| 36,884 | [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | A curated collection of 1000+ agent skills from official dev teams and the community, compatible with Claude C… |
| 36,712 | [DayuanJiang/next-ai-draw-io](https://github.com/DayuanJiang/next-ai-draw-io) | Draw and edit draw.io diagrams by chatting with an AI. Web app, desktop app, and an MCP server for Claude Code… |
| 33,384 | [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | Community plugin to control Blender 3D with any LLM of your choice. Not affiliated with the official Blender F… |
| 29,354 | [mastra-ai/mastra](https://github.com/mastra-ai/mastra) | Mastra is the modern TypeScript framework for AI-powered applications and agents. |
| 29,339 | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 410 Claude Code skills & agent skills & plugins (120+ Agents, custom commands, 410+ skills, customizable refer… |
| 29,328 | [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | AI-agent Skill for generating polished HTML slide decks: editorial magazine and Swiss layouts, image prompts, … |
| 28,775 | [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | Huashu Design 3.0 · 在 agent 里打一句话，拿回能交付的设计：网页 / App 原型 / 可编辑 PPTX / 动画 / 信息图 · 六个候选挑三个方向 · 84 种带样张的风格库 · 越用越懂你… |
| 26,930 | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | Open-source AI orchestration framework for building context-engineered, production-ready LLM applications. Des… |
| 26,883 | [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | Universal SEO skill for Claude Code. 26 sub-skills + 19 sub-agents covering technical SEO, E-E-A-T, schema, GE… |
| 25,341 | [pascalorg/editor](https://github.com/pascalorg/editor) | Open-source 3D architectural editor with a local CLI, MCP tools, and practical workflows for humans and AI age… |
| 23,199 | [comet-ml/opik](https://github.com/comet-ml/opik) | Debug, evaluate, and monitor your LLM applications, RAG systems, and agentic workflows with comprehensive trac… |
| 21,994 | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) | 数字生命卡兹克开源的 AI Skills 合集 \| Agent Skills: leader（帮你定义目标）, neat-freak 洁癖, hv-analysis, khazix-writer & more — Cl… |
| 21,509 | [1jehuang/jcode](https://github.com/1jehuang/jcode) | High performance coding agent harness written in Rust, built for heavy multi-agent dev workflows |
| 20,738 | [HBAI-Ltd/Toonflow-app](https://github.com/HBAI-Ltd/Toonflow-app) | 短剧、漫剧制作工具 Toonflow：开源 AI 视频创作平台，集成剧本创作、智能分镜、角色与场景资产管理、图像生成和视频生成。融合无限画布、AI Agent 与可视化工作流，支持本地部署、自选模型、跨平台客户端、MCP… |
| 18,082 | [Canner/WrenAI](https://github.com/Canner/WrenAI) | GenBI (Generative BI) for AI agents, an open-source, governed text-to-SQL through an open context layer that t… |
| 17,608 | [microsoft/mcp-for-beginners](https://github.com/microsoft/mcp-for-beginners) | This open-source curriculum introduces the fundamentals of Model Context Protocol (MCP) through real-world, cr… |
| 17,383 | [Evolink-AI/awesome-gpt-image-2-API-Prompts](https://github.com/Evolink-AI/awesome-gpt-image-2-API-Prompts) | GPT-Image-2 API and Prompts |
| 17,217 | [Vincentwei1021/video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | AI video skill for Claude Code & Codex — cinematic, editable product promos with Remotion: 124 shot recipe car… |
| 17,074 | [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat) | Open Source framework for voice agents, multimodal apps, and realtime AI. Maintained by Daily and the communit… |
| 16,168 | [GLips/Figma-Context-MCP](https://github.com/GLips/Figma-Context-MCP) | MCP server to provide Figma layout information to AI coding agents like Cursor |
| 15,729 | [CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp) | Unity MCP acts as a bridge between AI assistants and your Unity Editor. Give your LLM tools to manage assets, … |
| 15,548 | [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master) | A Claude skill that writes the accurate prompts for any AI tool. Zero tokens or credits wasted. Full context a… |
| 15,524 | [miuuyy/codex-chatgpt-web](https://github.com/miuuyy/codex-chatgpt-web) | Use ChatGPT Web (including Pro) as a native model in Codex — with context, tools, streaming and images, withou… |
| 15,098 | [livekit/agents](https://github.com/livekit/agents) | A framework for building realtime voice AI agents 🤖🎙️📹 |
| 14,884 | [apify/apify-mcp-server](https://github.com/apify/apify-mcp-server) | The Apify MCP server enables your AI agents to extract data from social media, search engines, maps, e-commerc… |
| 14,314 | [jub0t/Concat](https://github.com/jub0t/Concat) | Beta: The truly free, open-source, local-first, cross-platform video editor. Scriptable through a JSON-RPC API… |
| 14,175 | [krillinai/OpenCreator](https://github.com/krillinai/OpenCreator) | Formerly KrillinAI, VideoTranslation and Dubbing Tool for 120+ Languages. Open-source AI workspace for creator… |
| 14,131 | [OrchestratorInc/agent-orchestrator](https://github.com/OrchestratorInc/agent-orchestrator) | Plan, run and supervise fleets of agents from task to merged PR. Desktop (macOS, Windows, Linux) + iPhone & An… |
| 14,044 | [tangency-labs/solidcraft](https://github.com/tangency-labs/solidcraft) | SolidCraft: an open-source parametric 3D CAD application built in pure Rust. Desktop, web, and automation thro… |
| 14,010 | [ConardLi/garden-skills](https://github.com/ConardLi/garden-skills) | ConardLi's open-source Skills collection, featuring web design, knowledge retrieval, image generation, and mor… |
| 13,742 | [YouMind-OpenLab/awesome-nano-banana-pro-prompts](https://github.com/YouMind-OpenLab/awesome-nano-banana-pro-prompts) | 🍌 World's largest Nano Banana Pro prompt library — 10,000+ curated prompts with preview images, 16 languages. … |
| 13,713 | [modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk) | The official TypeScript SDK for Model Context Protocol servers and clients |
| 13,111 | [multimodal-art-projection/YuE](https://github.com/multimodal-art-projection/YuE) | YuE2: frontier music generation with symbolic planning, zero-shot covers, and agentic music editing. |
| 12,857 | [HKUDS/ViMax](https://github.com/HKUDS/ViMax) | "ViMax: Agentic Video Generation (Director, Screenwriter, Producer, and Video Generator All-in-One)" |
| 12,562 | [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) | A toolbox of film styles made in code for Claude Code: 66 ready to use, and your own. Each style is a style pr… |
| 12,220 | [kangarooking/cangjie-skill](https://github.com/kangarooking/cangjie-skill) | 把书、长视频、播客等高价值内容蒸馏成可执行的 Agent Skills（Distill high-value content from books, long-form videos, podcasts, and mor… |
| 11,777 | [genspark-ai/genoffice](https://github.com/genspark-ai/genoffice) | Free, open-source AI Office suite: Docs, Sheets, Slides, PDF, Markdown and HTML editors with a built-in AI age… |
| 11,526 | [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) | GEO-first SEO skill for Claude Code. Comprehensive AI search optimization for any website — citability scoring… |
| 11,417 | [moonshine-ai/moonshine](https://github.com/moonshine-ai/moonshine) | Very low latency speech to text, intent recognition, and text to speech, for building voice agents and interfa… |
| 11,217 | [TEN-framework/ten-framework](https://github.com/TEN-framework/ten-framework) | Open-source framework for conversational voice AI agents |
| 10,808 | [nicobailon/visual-explainer](https://github.com/nicobailon/visual-explainer) | Agent skill that generates rich HTML pages or slide decks for diagrams, diff reviews, plan audits, data tables… |
| 10,763 | [AgriciDaniel/claude-ads](https://github.com/AgriciDaniel/claude-ads) | Claude-first paid-media operations skill for Claude Code across 12 ad platforms (Google, Meta, YouTube, Linked… |
| 10,394 | [chuspeeism/dashi-ppt-skill](https://github.com/chuspeeism/dashi-ppt-skill) | An AI-agent skill that generates browser-editable presentations from multiple visual themes, exportable to HTM… |
| 10,305 | [ykdojo/claude-code-tips](https://github.com/ykdojo/claude-code-tips) | 45+ tips for getting the most out of Claude Code, from basics to advanced - includes a custom status line scri… |

## Top repositories — list B (content-generation tools)

| Stars | Repository | Description |
|---:|---|---|
| 205,459 | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | A feature-rich command-line audio/video downloader |
| 175,881 | [f/prompts.chat](https://github.com/f/prompts.chat) | f.k.a. Awesome ChatGPT Prompts. Share, discover, and collect prompts from the community. Free and open source … |
| 165,258 | [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | Stable Diffusion web UI |
| 145,191 | [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | The most powerful and modular diffusion model GUI, api and backend with a graph/nodes interface. The fastest l… |
| 139,647 | [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | 利用 AI 大模型和自动化工作流，根据主题或关键词一键生成高清短视频。Generate HD short videos from a topic or keyword with an automated AI workf… |
| 135,209 | [excalidraw/excalidraw](https://github.com/excalidraw/excalidraw) | Virtual whiteboard for sketching hand-drawn like diagrams |
| 116,349 | [stablyai/orca](https://github.com/stablyai/orca) | Orca is the place for working with a fleet of coding agents (e.g. Claude Code, Codex). Run any agent with your… |
| 111,321 | [paperclipai/paperclip](https://github.com/paperclipai/paperclip) | The open-source app everyone uses to manage agents at work |
| 106,076 | [nexu-io/open-design](https://github.com/nexu-io/open-design) | The 1st Collaborative AI Design Agent Workspace. Local-first and open source. Create motion, prototypes, websi… |
| 102,514 | [ruvnet/RuView](https://github.com/ruvnet/RuView) | π RuView turns commodity WiFi signals into real-time spatial intelligence, vital sign monitoring, and presence… |
| 101,615 | [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) | VoiceStudio is the open-source, fully-local ElevenLabs alternative — voice cloning, voice design, video dubbin… |
| 96,165 | [3b1b/manim](https://github.com/3b1b/manim) | Animation engine for explanatory math videos |
| 91,020 | [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid) | Generation of diagrams like flowcharts or sequence diagrams from text in a similar manner as markdown |
| 90,196 | [koala73/worldmonitor](https://github.com/koala73/worldmonitor) | Real-time global intelligence dashboard. AI-powered news aggregation, geopolitical monitoring, and infrastruct… |
| 79,074 | [unslothai/unsloth](https://github.com/unslothai/unsloth) | Local UI to run and train LLMs and diffusion models. Supports GGUF, MLX, Qwen3.8, DeepSeek-V4.1, MiniMax-H3, G… |
| 73,881 | [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master) | AI turns documents or topics into real, native PowerPoint decks—with native shapes, transitions and animations… |
| 70,971 | [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | 🎥      Make videos programmatically with React |
| 70,830 | [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) | Documented system prompts from Anthropic - Claude Fable 5.1, Opus 5.5, Claude Design, Claude Code. OpenAI - Ch… |
| 66,564 | [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) | Mirror of https://git.ffmpeg.org/ffmpeg.git |
| 64,922 | [RVC-Boss/GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | 1 min voice data can also be used to train a good TTS model! (few shot voice cloning) |
| 62,103 | [penpot/penpot](https://github.com/penpot/penpot) | Penpot: The open-source design platform for Product teams that need scalable collaboration. |
| 60,225 | [CorentinJ/Real-Time-Voice-Cloning](https://github.com/CorentinJ/Real-Time-Voice-Cloning) | Clone a voice in 5 seconds to generate arbitrary speech in real-time |
| 59,453 | [jamiepine/voicebox](https://github.com/jamiepine/voicebox) | The open-source AI voice studio. Clone, dictate, create. |
| 55,685 | [TryGhost/Ghost](https://github.com/TryGhost/Ghost) | Independent technology for modern publishing, memberships, subscriptions and newsletters. |
| 54,951 | [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Port of OpenAI's Whisper model in C/C++ |
| 53,821 | [lllyasviel/Fooocus](https://github.com/lllyasviel/Fooocus) | Focus on prompting and generating |
| 50,212 | [mudler/LocalAI](https://github.com/mudler/LocalAI) | LocalAI is the open-source AI engine. Run any model - LLMs, vision, voice, image, video - on any hardware. No … |
| 49,488 | [alibaba/open-code-review](https://github.com/alibaba/open-code-review) | Secure, fast, efficient, battle-tested at Alibaba's scale. Hybrid architecture code review tool: deterministic… |
| 49,379 | [slidevjs/slidev](https://github.com/slidevjs/slidev) | Presentation Slides for Developers |
| 46,184 | [coqui-ai/TTS](https://github.com/coqui-ai/TTS) | 🐸💬 - a deep learning toolkit for Text-to-Speech, battle-tested in research and production |
| 42,266 | [ManimCommunity/manim](https://github.com/ManimCommunity/manim) | A community-maintained Python framework for creating mathematical animations. |
| 41,157 | [codewhale-hq/Codewhale](https://github.com/codewhale-hq/Codewhale) | Open-source agent for the terminal written in Rust. Use any provider or model. Issues & PRs always welcome |
| 41,089 | [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM) | VoxCPM2: Tokenizer-Free TTS for Multilingual Speech Generation, Creative Voice Design, and True-to-Life Clonin… |
| 40,822 | [github/awesome-copilot](https://github.com/github/awesome-copilot) | Community-contributed instructions, agents, skills, and configurations to help you make the most of GitHub Cop… |
| 40,678 | [linshenkx/prompt-optimizer](https://github.com/linshenkx/prompt-optimizer) | An AI prompt optimizer for writing better prompts and getting better AI results. |
| 40,429 | [TeamNewPipe/NewPipe](https://github.com/TeamNewPipe/NewPipe) | A libre lightweight streaming front-end for Android. |
| 40,252 | [drawdb-io/drawdb](https://github.com/drawdb-io/drawdb) | Free, simple, and intuitive online database diagram editor and SQL generator. |
| 39,987 | [2noise/ChatTTS](https://github.com/2noise/ChatTTS) | A generative speech model for daily dialogue. |
| 39,059 | [RVC-Project/Retrieval-based-Voice-Conversion-WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) | Easily train a good VC model with voice data <= 10 mins! |
| 38,140 | [myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice) | Instant voice cloning by MIT and MyShell. Audio foundation model. |
| 37,375 | [xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Real-ESRGAN aims at developing Practical Algorithms for General Image/Video Restoration. |
| 36,879 | [babysor/MockingBird](https://github.com/babysor/MockingBird) | 🚀Clone a voice in 5 seconds to generate arbitrary speech in real-time |
| 36,135 | [carbon-app/carbon](https://github.com/carbon-app/carbon) | :black_heart: Create and share beautiful images of your source code |
| 35,491 | [freestylefly/awesome-gpt-image-2](https://github.com/freestylefly/awesome-gpt-image-2) | Prompt as Code \| GPT Image 2 / 2.5 提示词与案例库，530+ 个案例、20+ 套工业级模板与可复用 Skills，新增 2.5 同提示词对比专区，附完整提示词与生成记录，持续更新。 |
| 34,868 | [huggingface/diffusers](https://github.com/huggingface/diffusers) | 🤗 Diffusers: State-of-the-art diffusion models for image, video, and audio generation in PyTorch. |
| 32,463 | [Zackriya-Solutions/meetily](https://github.com/Zackriya-Solutions/meetily) | Privacy-first AI meeting note taker for Windows and macOS. Free, open source (MIT). On-device Whisper/Parakeet… |
| 32,387 | [Anil-matcha/Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) | Unrestricted Open-source alternative to AI video platforms — Free AI image & video generation studio with 600+… |
| 31,929 | [zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides) | Create beautiful slides on the web using a coding agent's frontend skills |
| 30,585 | [browser-use/video-use](https://github.com/browser-use/video-use) | Edit videos with coding agents |
| 30,362 | [JunkFood02/Seal](https://github.com/JunkFood02/Seal) | 🦭 Video/Audio Downloader for Android, based on yt-dlp |
| 29,994 | [labring/FastGPT](https://github.com/labring/FastGPT) | FastGPT is a knowledge-based platform built on the LLMs, offers a comprehensive suite of out-of-the-box capabi… |
| 29,789 | [ATH-MaaS/Pixelle-Video](https://github.com/ATH-MaaS/Pixelle-Video) | 🚀 AI 全自动短视频引擎 \| AI Fully Automated Short Video Engine |
| 29,637 | [alibaba/page-agent](https://github.com/alibaba/page-agent) | JavaScript in-page GUI agent. Control web interfaces with natural language. |
| 29,161 | [yamadashy/repomix](https://github.com/yamadashy/repomix) | 📦 Repomix is a powerful tool that packs your entire repository into a single, AI-friendly file. Perfect for wh… |
| 28,994 | [invoke-ai/InvokeAI](https://github.com/invoke-ai/InvokeAI) | Invoke is a leading creative engine for Stable Diffusion models, empowering professionals, artists, and enthus… |
| 28,130 | [hypit-ai/hypit](https://github.com/hypit-ai/hypit) | Clone any viral video with AI agents. Not just a script, the whole workflow: swap the face, the words, the B-r… |
| 28,060 | [svc-develop-team/so-vits-svc](https://github.com/svc-develop-team/so-vits-svc) | SoftVC VITS Singing Voice Conversion |
| 27,755 | [vercel/ai](https://github.com/vercel/ai) | The AI Toolkit for TypeScript. From the creators of Next.js, the AI SDK is a free open-source library for buil… |
| 27,120 | [onlook-dev/onlook](https://github.com/onlook-dev/onlook) | The Developer Tool for Visual Engineers • An Open-Source AI-First Design tool • Visually build, style, and edi… |
| 26,500 | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Faster Whisper transcription with CTranslate2 |

## Capabilities searched

Each capability below was searched for explicitly. The corpus in `skills/` was built to cover every one of them; where the survey found nothing usable, a skill was authored from scratch.

### video

- `text to video model`
- `video upscaling interpolation`
- `background removal video`
- `video editing ffmpeg`
- `short form video reels shorts pipeline`
- `remotion video`
- `comfyui video workflow`
- `video dubbing translation`
- `subtitle caption generation video`

### image

- `stable diffusion sdxl local`
- `comfyui image workflow`
- `background removal segmentation image`
- `thumbnail generation`
- `text to speech local tts`
- `image upscaling restoration`

### audio

- `voice cloning rvc`
- `lip sync wav2lip`
- `music generation audiocraft musicgen`
- `audio source separation demucs`
- `text to speech piper coqui kokoro`
- `speech recognition whisper transcription`

### design

- `slide deck presentation generation`
- `diagram mermaid excalidraw`
- `excalidraw`
- `3d blender rendering`
- `motion graphics animation`

### publishing

- `stock footage sourcing`
- `social media publishing scheduling`
- `seo content writing`
- `content management publishing`
