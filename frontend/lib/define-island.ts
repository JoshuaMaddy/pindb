import { mount, unmount, type Component } from "svelte";

// Every islands/<name>.entry.ts is two lines:
//   import Component from "./<name>/Component.svelte";
//   export default defineIsland(Component);
// The loader (mount.ts) calls the default export with the [data-island]
// element and its parsed JSON props, and keeps the returned unmount.
export function defineIsland<P extends Record<string, unknown>>(
  component: Component<P>,
) {
  return (target: HTMLElement, props: P): (() => void) => {
    const app = mount(component, { target, props });
    return () => void unmount(app);
  };
}
