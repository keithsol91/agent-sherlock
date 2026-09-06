(() => {
  const key = new URLSearchParams(window.location.search).get("industry") || "medical";
  const examples = window.SHERLOCK_SLACK_EXAMPLES;
  const example = Object.hasOwn(examples, key) ? examples[key] : examples.medical;
  document.title = example.label + " — Illustrative Slack conversation";
  const mention = document.createElement("span");
  mention.className = "mention";
  mention.textContent = "@Sherlock";
  document.getElementById("question").append(mention, example.question.slice(9));
  document.getElementById("answer").textContent = example.answer;
  example.clients.forEach(client => {
    const row = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = client.name;
    row.append(name, " — " + client.work);
    document.getElementById("client-list").append(row);
  });
  document.getElementById("answer-note").textContent = example.note;
  document.getElementById("next-step").textContent = example.next;
  example.sources.forEach(source => {
    const label = document.createElement("span");
    label.textContent = source;
    document.getElementById("sources").append(label);
  });
  document.documentElement.dataset.ready = "true";
})();
