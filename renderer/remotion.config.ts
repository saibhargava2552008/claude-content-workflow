import { Config } from "@remotion/cli/config";
import path from "path";

Config.setPublicDir(
  path.join(
    process.env.HOME || process.env.USERPROFILE || "~",
    ".content-workflow-cache",
    "renderer_public",
  ),
);
