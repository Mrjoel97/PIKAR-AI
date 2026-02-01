---
description: Pipeline for creating video content (social media, organic, promotional) using Remotion and Content Creation Agent
---

# Create Video Content Pipeline

This workflow guides the creation of programmatic videos for social media, marketing, and organic posts using Remotion (React).

1. **Define Requirements**
   - Identify the goal of the video (e.g., "social media post", "promo", "feature demo").
   - Determine the duration (e.g., 15s, 30s).
   - List key text, assets (images/logos), and color scheme.

2. **Generate Remotion Project**
   - The user should ask the **Content Creation Agent** to create a video.
   - Example Prompts:
     - "Create a video for social media about our new coffee blend."
     - "Generate a code for a 15s Instagram story announcing the sale."
     - "Make a promotional video for the analytics dashboard."
   - The Agent will use the `generate_remotion_video` tool to access the Remotion framework knowledge.

3. **Code Generation**
   - The Content Creation Agent will output a complete React component (e.g., `SocialVideo.tsx`).
   - This code will include:
     - `Composition` setup.
     - Animations using `useCurrentFrame` and `interpolate`.
     - Styling using inline styles or Tailwind (if configured).

4. **Implementation**
   - Copy the generated code to a new file in your Remotion project (e.g., `frontend/src/videos/SocialVideo.tsx`).
   - Register the composition in `frontend/src/Root.tsx` (or equivalent registry).
   - Add necessary assets to `public/` folder.

5. **Preview & Render**
   - Run the development server: `npm start` (or `npm run dev`).
   - Preview the video in the browser at `http://localhost:3000`.
   - Render the video: `npx remotion render SocialVideo out/video.mp4`.

## Agent Capabilities used
- **ContentCreationAgent**: Orchestrates the process.
- **generate_remotion_video**: Provides Remotion framework context for any video type.
- **remotion** (Skill): Provides technical implementation details.
