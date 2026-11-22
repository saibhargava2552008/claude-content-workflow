# Scene Components Catalog

Available scene primitives for composition in `claude-content-workflow`:

### 1. `title_card`
- **Purpose**: Big bold headline or question hook.
- **Properties**: `text`, `subtext`, `theme`, `animation`.

### 2. `talking_head`
- **Purpose**: Presenter video with background treatment and lower-third captions.
- **Properties**: `video_src`, `mask_style`, `background_blur`.

### 3. `broll`
- **Purpose**: Contextual imagery or screen recordings demonstrating the topic.
- **Properties**: `media_src`, `pan_zoom`, `filter`.

### 4. `code_snippet`
- **Purpose**: Syntax-highlighted code explanation with animated line focus.
- **Properties**: `code`, `language`, `highlight_lines`, `theme`.

### 5. `diagram`
- **Purpose**: Architecture, flowchart, or step-by-step concept illustration.
- **Properties**: `nodes`, `edges`, `active_step`.

### 6. `text_overlay`
- **Purpose**: Key bullet points, statistics, or emphasis quotes.
- **Properties**: `items`, `bullet_style`, `stagger_delay`.
