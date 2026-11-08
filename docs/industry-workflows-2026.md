# Adult AI creative workflows — evidence review (November 2026)

**Scope**: lawful adult fiction, roleplay, virtual characters and media production. This is an observed-process survey, not a census or proof of market share. Official product docs describe supported flows; community guides and reports are anecdotes; editorial judgments below are explicitly hypotheses.

## 1. Character roleplay

Observed flow: select local/hosted LLM → import character card → load scenario and world/lorebook → set context and sampler preset → chat/swipe/rewrite → summarize or extract key memory → continue/branch.

The LLM creates prose, but the client inserts memory and determines context; persistent states are externally recorded.

Sources: [SillyTavern world info](https://github.com/SillyTavern/SillyTavern-Docs/blob/main/Usage/worldinfo.md), [SillyTavern MemoryBooks](https://github.com/aikohanasaki/SillyTavern-MemoryBooks), [community author workflow](https://www.reddit.com/r/SillyTavernAI/comments/1qyoy9t/how_i_create_character_cards_in_sillytavern_and/).

## 2. Adult illustration and R34-style fictional content

Observed flow: select checkpoint/model family → select character/style LoRA and references → generate multiple drafts → choose candidates → inpaint/redraw individual areas → upscale → organize and export. In ComfyUI, the execution graph is made of explicit nodes; a language model is optional.

Sources: [ComfyUI workflow description](https://cloutstudio.ai/blog/nsfw-workflow-comfyui), [local image-generation guide](https://pornworks.life/guides/using-comfyui-for-nsfw-generation), [Manga Studio layering](https://github.com/ahmet360/manga-studio).

## 3. Manga/scanlation

Observed flow: page import → region/bubble detection → OCR → script review/translation → old text cleanup/inpainting → typesetting → QC → export. Human scanlation teams separate translator, cleaner, letterer and reviewer roles. Good frameworks allow box correction and fully local OCR even when translating using a cloud model.

Sources: [Libre Manga Translator](https://github.com/mrdhnto/libre-manga-translator), [ComiTrans](https://github.com/Aaaaamadeus/ComiTrans), [human scanlation roles](https://scanlate.io/about.html), [Manga Translation Studio](https://github.com/suphotP/manga-translation-studio).

## 4. Fiction writing

Observed flow: project/story and writing preset → memory and author's note → conditionally selected lorebook entries → write/continue text → manual revisions and branches → export. A model's context window is not reliable permanent memory. Many steps are editorial, not autonomous tool calls.

Sources: [NovelAI memory and author's note](https://docs.novelai.net/en/text/editor/storysettings/), [NovelAI lorebook](https://docs.novelai.net/en/text/lorebook/), [2026 study of AI fiction production patterns](https://arxiv.org/abs/2606.22748).

## 5. Adult video and virtual creators

Observed flow for a fictional AI persona: design verified-adult original identity → generate consistent stills → choose one as keyframe → image-to-video animation → quality inspection/edit → add disclosure → schedule or publish on permitted platform → manage subscriber messaging and analytics. Marketing claims should not be treated as evidence of creators' typical income or model success. For real-person likenesses, verified consent is necessary.

Sources: [Fanvue AI content policy](https://help.fanvue.com/en/articles/9538738-ai-content-on-fanvue-what-s-allowed), [Fanvue AI tools](https://help.fanvue.com/en/articles/9539500-ai-tools-on-fanvue), [video workflow vendor example](https://www.fanscreator.ai/blog/text-to-video-vs-image-to-video).

## 6. Adult games/visual novels

Observed flow: character/scene/asset registry → branches, flags, dialogue graph → backgrounds/sprites/audio → playable build → test unreachable branches, continuity and exports. The engine owns story state and branching logic. Models may draft dialogue and art, but runtime state must not depend on reliable autonomous tool calling.

Sources: [Ren'Py quickstart](https://www.renpy.org/doc/html/quickstart.html), [Twine](https://www.twinery.org/), [structured branching stories study](https://www.mdpi.com/2073-8994/18/1/113).

## Product implications

1. Build media-specific **repeatable pipelines** and expose manual touchpoints.
2. Treat creative assets, character definitions, regions and timeline edits as canonical artifacts; make models replaceable processors.
3. Export editable work; do not make a cloud chat history the only copy.
4. Keep an inference adapter for non-tool-calling local models. Reserve agent-style orchestration for genuinely exploratory tasks.
5. Avoid rebuilding mature OCR, inpainting and game engines. Integrate through permissioned, versioned adapters, considering license compatibility.
6. Do not conflate web traffic, popularity, creator revenue and willingness to pay for a new open-source creative tool.
7. Follow source and platform policies. For third-party content, maintain provenance and permission metadata; reject unauthorized mirror scraping and non-consensual personal likenesses.
