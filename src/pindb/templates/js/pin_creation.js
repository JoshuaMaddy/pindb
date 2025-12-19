window.addEventListener("load", function () {
  // -------------------------------
  // Link Add/Remove
  // -------------------------------

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

  // -------------------------------
  // Tom Select Initialization
  // -------------------------------

  document.querySelectorAll("select.multi-select").forEach((el) => {
    new TomSelect(el, {
      maxItems: null,
      plugins: ["caret_position", "remove_button"],
    });
  });

  document.querySelectorAll("select.single-select").forEach((el) => {
    new TomSelect(el, {});
  });

  // -------------------------------
  // Drag & Drop Upload Boxes
  // -------------------------------

  document.querySelectorAll(".image-drop").forEach((box) => {
    const inputId = box.dataset.inputId;
    const input = document.getElementById(inputId);

    box.addEventListener("click", () => input.click());

    input.addEventListener("change", () => {
      if (input.files[0]) showPreview(box, input.files[0]);
    });

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

  const limitedEditionSelected = [
    "bg-pin-main",
    "border-accent",
    "text-accent",
  ];

  limitedEditionYes.addEventListener("click", (e) => {
    e.preventDefault();
    limitedEditionCheckbox.value = true;
    limitedEditionYes.classList.add(...limitedEditionSelected);
    limitedEditionNo.classList.remove(...limitedEditionSelected);
  });

  limitedEditionNo.addEventListener("click", (e) => {
    e.preventDefault();
    limitedEditionCheckbox.value = false;
    limitedEditionNo.classList.add(...limitedEditionSelected);
    limitedEditionYes.classList.remove(...limitedEditionSelected);
  });
});
