import { downloadBlob } from "@/features/common/download";

/** Rasterise the displayed SVG, resolving CSS variables before serialisation. No data is fetched. */
export async function exportChartPng(svg: SVGSVGElement, description: string) {
  const clone = svg.cloneNode(true) as SVGSVGElement;
  const sources = [svg, ...svg.querySelectorAll("*")];
  const targets = [clone, ...clone.querySelectorAll("*")];
  sources.forEach((source, i) => {
    const style = getComputedStyle(source);
    for (const property of ["fill", "stroke", "stroke-width", "stroke-dasharray", "font-family", "font-size", "font-weight", "opacity"]) {
      (targets[i] as SVGElement).style.setProperty(property, style.getPropertyValue(property));
    }
  });
  const { width, height } = svg.getBoundingClientRect();
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", String(width)); clone.setAttribute("height", String(height));
  const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: "image/svg+xml" }));
  try {
    const picture = new Image(); picture.src = url; await picture.decode();
    const canvas = document.createElement("canvas");
    // Include the scientific description in the exported image itself.
    canvas.width = Math.ceil(width * 2); canvas.height = Math.ceil((height + 60) * 2);
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Image export unavailable");
    context.scale(2, 2); context.fillStyle = "#ffffff"; context.fillRect(0, 0, width, height + 60);
    context.drawImage(picture, 0, 0, width, height);
    context.fillStyle = "#14213d"; context.font = "12px sans-serif";
    context.fillText(description, 8, height + 20, width - 16);
    context.fillText("Validation evidence · Costs, where shown, are hypothetical NCU.", 8, height + 40, width - 16);
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob((b) => b ? resolve(b) : reject(new Error("Image export unavailable")), "image/png"));
    downloadBlob(blob, "validation_chart.png");
  } finally { URL.revokeObjectURL(url); }
}
