package com.example.myapplication.models;

import com.google.gson.annotations.SerializedName;

public class RegisterRequest {
    @SerializedName("service_number")
    private String serviceNumber;

    @SerializedName("email")
    private String email;

    @SerializedName("password")
    private String password;

    @SerializedName("first_name")
    private String firstName;

    @SerializedName("last_name")
    private String lastName;

    @SerializedName("rank")
    private String rank;

    @SerializedName("unit")
    private String unit;

    @SerializedName("phone")
    private String phone;

    public RegisterRequest(String serviceNumber, String email, String password,
                           String firstName, String lastName, String rank,
                           String unit, String phone) {
        this.serviceNumber = serviceNumber;
        this.email = email;
        this.password = password;
        this.firstName = firstName;
        this.lastName = lastName;
        this.rank = rank;
        this.unit = unit;
        this.phone = phone;
    }

    public String getServiceNumber() { return serviceNumber; }
    public String getEmail() { return email; }
    public String getPassword() { return password; }
    public String getFirstName() { return firstName; }
    public String getLastName() { return lastName; }
    public String getRank() { return rank; }
    public String getUnit() { return unit; }
    public String getPhone() { return phone; }
}
