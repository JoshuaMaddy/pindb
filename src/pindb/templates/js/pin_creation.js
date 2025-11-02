window.addEventListener("load", function () {
  const ADD_LINK_BUTTON = document.getElementById("add-link-button");
  const REMOVE_BUTTONS = document.querySelectorAll(".remove-link-button");
  ADD_LINK_BUTTON.addEventListener("click", addLink);
  REMOVE_BUTTONS.forEach((el) => {
    el.addEventListener("click", (event) => {
      removeLink(event.currentTarget);
    });
  });

  const LINKS_DIV = document.getElementById("links");
  const BASE_LINK = document.getElementById("link_0");
  if (BASE_LINK === null || LINKS_DIV === null) {
    console.error("No first link found!");
    return;
  }
  var links = Array.from(document.querySelectorAll("#links > input"));

  const REMOVE_BUTTON = document.createElement("button");
  REMOVE_BUTTON.innerText = "Remove";

  function addLink() {
    /**
     * @type {HTMLElement}
     */
    var new_link = BASE_LINK.cloneNode();
    new_link.id = `link_${links.length}`;
    new_link.value = "";
    new_link.classList.remove("col-span-2");
    /**
     * @type {HTMLButtonElement}
     */
    var new_remove_button = REMOVE_BUTTON.cloneNode(true);
    new_remove_button.dataset.link_id = `link_${links.length}`;
    new_remove_button.addEventListener("click", (event) => {
      removeLink(event.currentTarget);
    });

    LINKS_DIV.appendChild(new_link);
    LINKS_DIV.appendChild(new_remove_button);

    links.push(new_link);
  }

  /**
   *
   * @param {HTMLButtonElement} button
   */
  function removeLink(button) {
    links = links.filter((link) => link.id !== button.dataset.link_id);
    button.previousSibling.remove();
    button.remove();
  }

  // Tom Select Init
  document.querySelectorAll("select.multi-select").forEach((el) => {
    let settings = {
      maxItems: null,
      plugins: ["caret_position", "remove_button"],
    };
    new TomSelect(el, settings);
  });

  document.querySelectorAll("select.single-select").forEach((el) => {
    let settings = {};
    new TomSelect(el, settings);
  });
});
