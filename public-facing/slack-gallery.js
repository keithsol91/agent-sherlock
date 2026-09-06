(() => {
  const examples = window.SHERLOCK_SLACK_EXAMPLES;
  const picker = document.getElementById("slack-industry-picker");
  if (!examples || !picker) return;

  function paragraph(parent, text, speaker) {
    const p = document.createElement("p");
    if (speaker) {
      const label = document.createElement("strong");
      label.textContent = speaker + ": ";
      p.append(label);
    }
    p.append(text);
    parent.append(p);
  }

  function showExample(key, announce) {
    if (!Object.hasOwn(examples, key)) return;
    const example = examples[key];
    const image = document.getElementById("slack-screenshot");
    document.getElementById("slack-mobile-image").srcset = "assets/examples/slack-" + key + "-mobile.png";
    image.src = "assets/examples/slack-" + key + "-desktop.png";
    image.alt = example.alt;
    document.getElementById("slack-screenshot-link").href = image.getAttribute("src");
    document.getElementById("slack-industry-caption").textContent = example.label + " experience";
    picker.querySelectorAll("button").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.industry === key)));

    const transcript = document.getElementById("slack-transcript-copy");
    transcript.replaceChildren();
    paragraph(transcript, example.question, "Alex");
    paragraph(transcript, example.answer, "Agent Sherlock");
    const clients = document.createElement("ul");
    example.clients.forEach(client => {
      const row = document.createElement("li");
      const name = document.createElement("strong");
      name.textContent = client.name;
      row.append(name, " — " + client.work);
      clients.append(row);
    });
    transcript.append(clients);
    paragraph(transcript, example.note);
    paragraph(transcript, "Example sources: " + example.sources.join("; ") + ".");
    paragraph(transcript, example.next);
    if (announce) document.getElementById("slack-gallery-status").textContent = "Showing the " + example.label.toLowerCase() + " Slack example.";
  }

  picker.addEventListener("click", event => {
    const button = event.target.closest("button[data-industry]");
    if (button) showExample(button.dataset.industry, true);
  });
  showExample("medical", false);
  picker.hidden = false;
})();
