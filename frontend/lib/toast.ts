// Bridge to the app toast bus: pindb_shell.js listens for "pindbToast"
// CustomEvents and routes them into Notyf.
export function dispatchToast(
  message: string,
  type: "success" | "error" = "success",
): void {
  document.dispatchEvent(
    new CustomEvent("pindbToast", { detail: { message, type } }),
  );
}
