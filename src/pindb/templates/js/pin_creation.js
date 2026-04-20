window.addEventListener("load", function () {
  // -------------------------------
  // Link Add/Remove
  // -------------------------------
  /*
  const addLinkButton = document.getElementById("add-link-button");
  const removeButtons = document.querySelectorAll(".remove-link-button");
  const linksDiv = document.getElementById("links");
  const baseLink = document.getElementById("link_0");

  if (!baseLink || !linksDiv) {
    console.error("No first link found!");
    return;
  }

  let links = Array.from(document.querySelectorAll("#links > input"));
  const removeButtonTemplate = document.createElement("button");
  removeButtonTemplate.innerText = "Remove";

  addLinkButton.addEventListener("click", addLink);

  removeButtons.forEach((el) => {
    el.addEventListener("click", (event) => removeLink(event.currentTarget));
  });

  function addLink() {
    const newLink = baseLink.cloneNode();
    newLink.id = `link_${links.length}`;
    newLink.value = "";
    newLink.classList.remove("col-span-2");

    const newRemoveButton = removeButtonTemplate.cloneNode(true);
    newRemoveButton.dataset.link_id = newLink.id;
    newRemoveButton.addEventListener("click", (event) =>
      removeLink(event.currentTarget)
    );

    linksDiv.appendChild(newLink);
    linksDiv.appendChild(newRemoveButton);

    links.push(newLink);
  }

  function removeLink(button) {
    links = links.filter((link) => link.id !== button.dataset.link_id);
    button.previousSibling.remove();
    button.remove();
  }
  */
 
  // -------------------------------
  // Tom Select Initialization
  // -------------------------------

  const _PIN_FORM_REF = window.PIN_FORM_REF;

  const _noResultsRender = {
    no_results: (data) => {
      const msg = data.input && data.input.length > 0 ? "No results found" : "Start typing to search…";
      return `<div class="no-results">${msg}</div>`;
    },
  };

  document.querySelectorAll("select.multi-select").forEach((el) => {
    const entityType = el.dataset.entityType;
    if (entityType && _PIN_FORM_REF) {
      const opts = {
        load: (query, callback) => {
          fetch(
            `${_PIN_FORM_REF.optionsBaseUrl}/${entityType}?q=${encodeURIComponent(query)}`
          )
            .then((res) => res.json())
            .then(callback)
            .catch(() => callback());
        },
        shouldLoad: (q) => q.length > 0,
        maxItems: null,
        plugins: ["caret_position", "remove_button"],
        valueField: "value",
        labelField: "text",
        searchField: "text",
        persist: true,
        render: { ..._noResultsRender },
      };
      if (entityType === "tag") {
        opts.render = {
          ..._noResultsRender,
          item: TagSelect.tagItemRender,
          option: TagSelect.tagOptionRender,
        };
        Object.assign(opts, TagSelect.tagSelectLucideCallbacks());
      }
      new TomSelect(el, opts);
    } else {
      new TomSelect(el, {
        maxItems: null,
        plugins: ["caret_position", "remove_button"],
      });
    }
  });

  document.querySelectorAll("select.single-select").forEach((el) => {
    new TomSelect(el, {});
  });

  // -------------------------------
  // Drag & Drop Upload Boxes
  // -------------------------------

  let _hoveredImageBox = null;

  document.querySelectorAll(".image-drop").forEach((box) => {
    const inputId = box.dataset.inputId;
    const input = document.getElementById(inputId);

    box.addEventListener("click", () => input.click());

    input.addEventListener("change", () => {
      if (input.files[0]) showPreview(box, input.files[0]);
    });

    box.addEventListener("mouseenter", () => { _hoveredImageBox = { box, input }; });
    box.addEventListener("mouseleave", () => { _hoveredImageBox = null; });

    box.addEventListener("dragover", (e) => {
      e.preventDefault();
      box.classList.replace("border-pin-border", "border-accent");
    });

    box.addEventListener("dragleave", () => {
      box.classList.replace("border-accent", "border-pin-border");
    });

    box.addEventListener("drop", (e) => {
      e.preventDefault();
      box.classList.remove("border-pin-border");
      box.classList.add("border-accent");

      const file = e.dataTransfer.files[0];
      if (!file) return;

      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;

      showPreview(box, file);
    });
  });

  document.addEventListener("paste", (e) => {
    if (!_hoveredImageBox) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (!file) continue;
        const dt = new DataTransfer();
        dt.items.add(file);
        _hoveredImageBox.input.files = dt.files;
        showPreview(_hoveredImageBox.box, file);
        e.preventDefault();
        break;
      }
    }
  });

  function showPreview(box, file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      box.style.backgroundImage = `url('${e.target.result}')`;
      box.textContent = "";
    };
    reader.readAsDataURL(file);
  }

  // -------------------------------
  // Limited Edition
  // -------------------------------

  const limitedEditionCheckbox = document.getElementById("limited_edition");
  const limitedEditionYes = document.getElementById("limited_edition_yes");
  const limitedEditionNo = document.getElementById("limited_edition_no");

  if (limitedEditionCheckbox && limitedEditionYes && limitedEditionNo) {
    const limitedEditionSelected = [
      "bg-pin-main",
      "border-accent",
      "text-accent",
    ];

    limitedEditionYes.addEventListener("click", (e) => {
      e.preventDefault();
      limitedEditionCheckbox.checked = true;
      limitedEditionCheckbox.value = "true";
      limitedEditionYes.classList.add(...limitedEditionSelected);
      limitedEditionNo.classList.remove(...limitedEditionSelected);
    });

    limitedEditionNo.addEventListener("click", (e) => {
      e.preventDefault();
      limitedEditionCheckbox.checked = true;
      limitedEditionCheckbox.value = "false";
      limitedEditionNo.classList.add(...limitedEditionSelected);
      limitedEditionYes.classList.remove(...limitedEditionSelected);
    });
  }
});
