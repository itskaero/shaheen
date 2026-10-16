import { Config } from "@remotion/cli/config";

// Use the machine's Playwright headless shell when present instead of
// downloading Chrome; override with REMOTION_BROWSER=/path/to/chrome.
const browser = process.env.REMOTION_BROWSER ?? "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
import { existsSync } from "node:fs";
if (existsSync(browser)) Config.setBrowserExecutable(browser);

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(92);
Config.setCodec("h264");
Config.setCrf(17);
Config.setPixelFormat("yuv420p");
Config.setConcurrency(4);
