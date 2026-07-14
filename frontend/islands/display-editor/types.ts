export type SizeHint = "normal" | "wide" | "tall" | "large";

export type ObjectFit = "cover" | "contain" | "fill";

export type PinOption = { value: string; text: string; thumbnail?: string };

export type DisplayImage = {
  id: number;
  guid: string;
  caption: string;
  sizeHint: SizeHint;
  objectFit: ObjectFit;
  position: number;
  pins: PinOption[];
};

export type DisplayEditorProps = {
  layout: string;
  maxImages: number;
  images: DisplayImage[];
  uploadUrl: string;
  reorderUrl: string;
  updateDisplayUrl: string;
  imageBaseUrl: string;
  pinOptionsUrl: string;
  viewUrl: string;
  thumbUrlPrefix: string;
};
