/* Fictional demonstration data only. No customer or Slack records. */
window.SHERLOCK_SLACK_EXAMPLES = {
  medical: {
    label: "Medical",
    question: "@Sherlock who have we worked with in the medical space?",
    answer: "I found 3 medical clients in the project history available to me:",
    clients: [
      { name: "Pine & Vale Health", work: "Social content and community management." },
      { name: "Orchard Medical Group", work: "Patient education campaign." },
      { name: "Beaconwell Clinics", work: "Recruitment content and employer branding." }
    ],
    note: "That’s 3 distinct clients with recorded project work. I’ve kept pitches and unconfirmed opportunities out of the count.",
    next: "I can narrow this to a service or pull together a short experience summary for your next conversation.",
    sources: ["Client case files", "Project history"],
    alt: "Illustrative Slack screenshot: a teammate asks about medical experience and Sherlock lists three fictional clients and their project work."
  },
  finance: {
    label: "Finance",
    question: "@Sherlock how many clients have we worked with in finance, and who were they?",
    answer: "I found 2 finance clients in the project history available to me:",
    clients: [
      { name: "Northline Credit Union", work: "Brand launch and financial education content." },
      { name: "Westbridge Capital", work: "Thought leadership and executive social content." }
    ],
    note: "That’s 2 distinct clients, rather than a count of every project. Both have recorded work; a proposal alone doesn’t count.",
    next: "For a new finance prospect, I can help you find the closest example by audience, service, or project type.",
    sources: ["Account history", "Project notes"],
    alt: "Illustrative Slack screenshot: a teammate asks how many finance clients the team has worked with and Sherlock names two fictional clients."
  },
  automotive: {
    label: "Automotive",
    question: "@Sherlock who have we worked with in automotive? What did we do for them?",
    answer: "I found 3 automotive clients in the project history available to me:",
    clients: [
      { name: "Summitline Motors", work: "Vehicle launch content and social strategy." },
      { name: "Oakway Auto Group", work: "Local dealership content and community management." },
      { name: "Motorwell Parts", work: "Product education and creator-led content." }
    ],
    note: "These are 3 distinct clients with recorded work. The list reflects the history I can access, so it may not include every past engagement.",
    next: "I can separate dealership work from manufacturer and aftermarket experience if that helps.",
    sources: ["Client case files", "Account history"],
    alt: "Illustrative Slack screenshot: a teammate asks about automotive experience and Sherlock lists three fictional clients with the work performed."
  }
};
