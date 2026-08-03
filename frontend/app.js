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
            service.responseTime === null
                ? "Unavailable"
                : `${service.responseTime} ms`;

        card.innerHTML = `
            <span class="status ${service.status}">
                ${service.status.toUpperCase()}
            </span>
            <h3>${service.name}</h3>
            <p>${service.url}</p>
            <p><strong>Response time:</strong> ${responseTime}</p>
            <p><strong>Uptime:</strong> ${service.uptime}%</p>
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

document
    .querySelector("#refresh-button")
    .addEventListener("click", displayServices);

displayServices();