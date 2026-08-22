const defaultServices = [
    {
        name: "Example Website",
        url: "https://example.com/",
        history: [
            { status: "online", responseTime: 140 },
            { status: "online", responseTime: 152 },
            { status: "online", responseTime: 135 },
            { status: "online", responseTime: 148 }
        ]
    },
    {
        name: "GitHub",
        url: "https://github.com/",
        history: [
            { status: "online", responseTime: 205 },
            { status: "online", responseTime: 192 },
            { status: "offline", responseTime: null },
            { status: "online", responseTime: 198 }
        ]
    },
    {
        name: "Test API",
        url: "https://test-api.example/",
        history: [
            { status: "online", responseTime: 310 },
            { status: "offline", responseTime: null },
            { status: "offline", responseTime: null },
            { status: "online", responseTime: 287 }
        ]
    }
];

function copyDefaultServices() {
    return JSON.parse(JSON.stringify(defaultServices));
}

function loadServices() {
    const savedServices =
        localStorage.getItem("cloudpulse-services");

    if (savedServices === null) {
        return copyDefaultServices();
    }

    try {
        const parsedServices = JSON.parse(savedServices);

        if (!Array.isArray(parsedServices)) {
            return copyDefaultServices();
        }

        return parsedServices;
    } catch (error) {
        console.error("Could not load saved services:", error);
        return copyDefaultServices();
    }
}

function saveServices() {
    localStorage.setItem(
        "cloudpulse-services",
        JSON.stringify(services)
    );
}

let services = loadServices();

function calculateMetrics(service) {
    const totalChecks = service.history.length;

    if (totalChecks === 0) {
        return {
            status: "pending",
            latestResponseTime: null,
            averageResponseTime: null,
            uptime: null,
            totalChecks: 0
        };
    }

    const latestCheck = service.history[totalChecks - 1];

    const successfulChecks = service.history.filter(
        (check) => check.status === "online"
    );

    const uptime = (
        (successfulChecks.length / totalChecks) *
        100
    ).toFixed(1);

    const responseTimes = successfulChecks
        .map((check) => check.responseTime)
        .filter((responseTime) => responseTime !== null);

    const averageResponseTime =
        responseTimes.length === 0
            ? null
            : Math.round(
                responseTimes.reduce(
                    (total, responseTime) => total + responseTime,
                    0
                ) / responseTimes.length
            );

    return {
        status: latestCheck.status,
        latestResponseTime: latestCheck.responseTime,
        averageResponseTime: averageResponseTime,
        uptime: uptime,
        totalChecks: totalChecks
    };
}

function displayServices() {
    const serviceList = document.querySelector("#service-list");
    serviceList.innerHTML = "";

    services.forEach((service) => {
        const metrics = calculateMetrics(service);
        const card = document.createElement("article");

        card.className = "service-card";

        const latestResponse =
            metrics.status === "pending"
                ? "Not checked yet"
                : metrics.latestResponseTime === null
                    ? "Unavailable"
                    : `${metrics.latestResponseTime} ms`;

        const averageResponse =
            metrics.averageResponseTime === null
                ? "Not available"
                : `${metrics.averageResponseTime} ms`;

        const uptime =
            metrics.uptime === null
                ? "Not calculated"
                : `${metrics.uptime}%`;

        card.innerHTML = `
            <span class="status ${metrics.status}">
                ${metrics.status.toUpperCase()}
            </span>
            <h3>${service.name}</h3>
            <p>${service.url}</p>
            <p>
                <strong>Latest response:</strong>
                ${latestResponse}
            </p>
            <p>
                <strong>Average response:</strong>
                ${averageResponse}
            </p>
            <p>
                <strong>Uptime:</strong>
                ${uptime}
            </p>
            <p>
                <strong>Total checks:</strong>
                ${metrics.totalChecks}
            </p>
        `;

        serviceList.appendChild(card);
    });

    updateSummary();
}

function updateSummary() {
    const statuses = services.map(
        (service) => calculateMetrics(service).status
    );

    const onlineCount = statuses.filter(
        (status) => status === "online"
    ).length;

    const offlineCount = statuses.filter(
        (status) => status === "offline"
    ).length;

    document.querySelector("#total-services").textContent =
        services.length;

    document.querySelector("#online-services").textContent =
        onlineCount;

    document.querySelector("#offline-services").textContent =
        offlineCount;
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
        history: []
    });
    
    saveServices();
    displayServices();

    document.querySelector("#monitor-form").reset();

    formMessage.textContent =
        `${name} was successfully added to CloudPulse.`;
}

function simulateCheck(service) {
    // Temporary simulation until the Python backend is connected.
    const isOnline = Math.random() > 0.2;

    const check = {
        status: isOnline ? "online" : "offline",
        responseTime: isOnline
            ? Math.floor(Math.random() * 350) + 75
            : null
    };

    service.history.push(check);

    // Keep only the 20 most recent checks.
    if (service.history.length > 20) {
        service.history.shift();
    }
}

function refreshServices() {
    const refreshButton =
        document.querySelector("#refresh-button");

    refreshButton.disabled = true;
    refreshButton.textContent = "Checking...";

    services.forEach(simulateCheck);
    saveServices();

    setTimeout(() => {
        displayServices();
        refreshButton.disabled = false;
        refreshButton.textContent = "Refresh";
    }, 500);
}

document
    .querySelector("#refresh-button")
    .addEventListener("click", refreshServices);

document
    .querySelector("#monitor-form")
    .addEventListener("submit", handleFormSubmission);

displayServices();