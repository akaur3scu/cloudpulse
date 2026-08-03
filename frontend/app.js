const services = [
    {
        name: "Example Website",
        url: "https://example.com",
        status: "online",
        responseTime: 146,
        uptime: 99.9
    },
    {
        name: "GitHub",
        url: "https://github.com",
        status: "online",
        responseTime: 203,
        uptime: 99.8
    },
    {
        name: "Test API",
        url: "https://test-api.example",
        status: "offline",
        responseTime: null,
        uptime: 92.4
    }
];

function displayServices() {
    const serviceList = document.querySelector("#service-list");
    serviceList.innerHTML = "";

    services.forEach((service) => {
        const card = document.createElement("article");
        card.className = "service-card";

        const responseTime =
            service.status === "pending"
                ? "Not checked yet"
                : service.responseTime === null
                    ? "Unavailable"
                    : `${service.responseTime} ms`;

        const uptime =
            service.uptime === null
                ? "Not calculated"
                : `${service.uptime}%`;

        card.innerHTML = `
            <span class="status ${service.status}">
                ${service.status.toUpperCase()}
            </span>
            <h3>${service.name}</h3>
            <p>${service.url}</p>
            <p><strong>Response time:</strong> ${responseTime}</p>
            <p><strong>Uptime:</strong> ${uptime}</p>
        `;

        serviceList.appendChild(card);
    });

    updateSummary();
}

function updateSummary() {
    const onlineCount = services.filter(
        (service) => service.status === "online"
    ).length;

    document.querySelector("#total-services").textContent =
        services.length;

    document.querySelector("#online-services").textContent =
        onlineCount;

    document.querySelector("#offline-services").textContent =
        services.length - onlineCount;
}

function handleFormSubmission(event) {
    event.preventDefault();

    const nameInput = document.querySelector("#service-name");
    const urlInput = document.querySelector("#service-url");
    const formMessage = document.querySelector("#form-message");

    const name = nameInput.value.trim();
    const url = urlInput.value.trim();

    formMessage.classList.remove("error-message");

    if (!name || !url) {
        formMessage.textContent =
            "Please provide both a service name and URL.";
        formMessage.classList.add("error-message");
        return;
    }

    let parsedUrl;

    try {
        parsedUrl = new URL(url);
    } catch {
        formMessage.textContent =
            "Please enter a valid URL, including https://";
        formMessage.classList.add("error-message");
        return;
    }

    if (
        parsedUrl.protocol !== "http:" &&
        parsedUrl.protocol !== "https:"
    ) {
        formMessage.textContent =
            "CloudPulse only supports HTTP and HTTPS URLs.";
        formMessage.classList.add("error-message");
        return;
    }

    const alreadyExists = services.some(
        (service) => service.url === parsedUrl.href
    );

    if (alreadyExists) {
        formMessage.textContent =
            "That website is already being monitored.";
        formMessage.classList.add("error-message");
        return;
    }

    services.push({
        name: name,
        url: parsedUrl.href,
        status: "pending",
        responseTime: null,
        uptime: null
    });

    displayServices();

    document.querySelector("#monitor-form").reset();

    formMessage.textContent =
        `${name} was successfully added to CloudPulse.`;
}


document
    .querySelector("#refresh-button")
    .addEventListener("click", displayServices);

document
    .querySelector("#monitor-form")
    .addEventListener("submit", handleFormSubmission);

displayServices();