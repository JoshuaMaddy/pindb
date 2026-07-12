export type SizeHint = "normal" | "feature";

export type PinOption = { value: string; text: string };

export type DisplayImage = {
  id: number;
  guid: string;
  caption: string;
  sizeHint: SizeHint;
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
