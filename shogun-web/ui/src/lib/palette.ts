/** Parse hex color to HSL. Returns [hue, saturation, lightness]. */
export function hexToHsl(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;

  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;

  if (max === min) return [0, 0, Math.round(l * 100)];

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

  let h = 0;
  switch (max) {
    case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
    case g: h = ((b - r) / d + 2) / 6; break;
    case b: h = ((r - g) / d + 4) / 6; break;
  }

  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
}

/** Generate N visually distinct colors, stepping hue around the base. */
export function generatePalette(baseColor: string, count: number): string[] {
  if (count <= 1) return [baseColor];

  const [h, s, l] = hexToHsl(baseColor);
  const step = 360 / count;
  const palette: string[] = [];

  for (let i = 0; i < count; i++) {
    const hue = (h + i * step) % 360;
    palette.push(`hsl(${Math.round(hue)}, ${Math.max(40, s)}%, ${Math.max(45, Math.min(65, l))}%)`);
  }

  return palette;
}

/** Return chart color(s) — single for 1, palette for many. */
export function chartColors(baseColor: string, count: number): string[] {
  return count > 1 ? generatePalette(baseColor, count) : [baseColor];
}