import joblib


model = joblib.load(
    "model.pkl"
)


print("==============================")
print("HELPGENIE AI TEST")
print("==============================")

while True:

    ticket = input(
        "\nEnter IT problem "
        "(type exit to stop): "
    )

    if ticket.lower() == "exit":
        break

    prediction = model.predict(
        [ticket]
    )[0]

    probabilities = model.predict_proba(
        [ticket]
    )[0]

    confidence = max(
        probabilities
    ) * 100

    print(
        "\nPredicted Category:",
        prediction
    )

    print(
        f"Confidence: {confidence:.2f}%"
    )