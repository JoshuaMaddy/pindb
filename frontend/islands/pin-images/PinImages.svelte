<script lang="ts">
  import ImageDropBox from "./ImageDropBox.svelte";

  type Side = { existingUrl: string | null };

  let { front, back }: { front: Side; back: Side } = $props();
</script>

<ImageDropBox
  inputId="front_image"
  previewId="front_image_preview"
  existingUrl={front.existingUrl}
  pinField="front"
>
  Front Image<span class="text-error-main ml-0.5">*</span>
</ImageDropBox>
<ImageDropBox
  inputId="back_image"
  previewId="back_image_preview"
  existingUrl={back.existingUrl}
  stackClass="flex-col gap-1"
>
  <p>Back Image</p>
  <i>(Optional)</i>
</ImageDropBox>
