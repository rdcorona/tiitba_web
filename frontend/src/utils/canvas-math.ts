/**
 * Coordinate transforms between display canvas and original image pixels.
 */

export interface Transform {
  offsetX: number;
  offsetY: number;
  scale: number;
}

export function displayToImage(
  dx: number, dy: number,
  transform: Transform,
  displayScale: number,
): { x: number; y: number } {
  const imgDisplayX = (dx - transform.offsetX) / transform.scale;
  const imgDisplayY = (dy - transform.offsetY) / transform.scale;
  return {
    x: Math.round(imgDisplayX / displayScale),
    y: Math.round(imgDisplayY / displayScale),
  };
}

export function imageToDisplay(
  ix: number, iy: number,
  transform: Transform,
  displayScale: number,
): { x: number; y: number } {
  return {
    x: ix * displayScale * transform.scale + transform.offsetX,
    y: iy * displayScale * transform.scale + transform.offsetY,
  };
}
