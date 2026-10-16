// Fonts from the site (Inter, Instrument Serif, Noto Nastaliq Urdu), bundled
// from @fontsource so the render never depends on Google Fonts at runtime.
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/700.css";
import "@fontsource/inter/800.css";
import "@fontsource/inter/900.css";
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";
import "@fontsource/noto-nastaliq-urdu/500.css";
import { continueRender, delayRender } from "remotion";

const handle = delayRender("Loading fonts");
Promise.all(
  [
    "400 20px Inter",
    "700 20px Inter",
    "800 20px Inter",
    "900 20px Inter",
    "20px 'Instrument Serif'",
    "italic 20px 'Instrument Serif'",
    "500 20px 'Noto Nastaliq Urdu'",
  ].map((font) => document.fonts.load(font, font.includes("Nastaliq") ? "بلندیوں" : "Aa")),
).then(
  () => continueRender(handle),
  () => continueRender(handle),
);
