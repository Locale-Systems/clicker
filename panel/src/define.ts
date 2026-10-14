// A class decorator like Lit's @customElement that skips names already
// defined. When Home Assistant restarts with a rebuilt panel, an open page
// loads the new module next to the old one; defining the same elements again
// would throw, so the page keeps the old ones until it is reloaded.

export const define =
  (name: string) =>
  (cls: CustomElementConstructor): void => {
    if (!customElements.get(name)) customElements.define(name, cls);
  };
