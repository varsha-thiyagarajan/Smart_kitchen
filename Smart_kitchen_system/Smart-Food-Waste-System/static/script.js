function predict() {

    let data = {
        family_size: document.getElementById("family_size").value,
        food_quantity: document.getElementById("food_quantity").value,
        storage_days: document.getElementById("storage_days").value,
        item_type: document.getElementById("item_type").value
    };

    fetch("/predict", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {

        if(result.error){
            alert(result.error);
            return;
        }

        document.getElementById("waste").innerText =
            "Predicted Waste: " + result.predicted_waste_kg + " kg";

        document.getElementById("risk").innerText =
            "Risk Level: " + result.risk_level;
    })
    .catch(error => {
        console.error(error);
        alert("Error connecting to server");
    });
}