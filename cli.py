# cli.py
import os
from app import app, db
from models import Donation, User, ResourceRoute, ChildLocation, ChildProfile

@app.cli.command('initdb')
def initdb():
    """
    Initializes the database and seeds it with sample donation data,
    resource routes, child location data, child profiles, and test users.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Seed donation data
        donation_samples = [
            Donation(
                origin_lat=-33.9249, origin_lon=18.4241,
                destination_lat=-29.8587, destination_lon=31.0218,
                donation_size=5000, donation_need="Medical Supplies"
            ),
            Donation(
                origin_lat=-33.9249, origin_lon=18.4241,
                destination_lat=-26.2041, destination_lon=28.0473,
                donation_size=3000, donation_need="Food Supplies"
            ),
            Donation(
                origin_lat=-33.9249, origin_lon=18.4241,
                destination_lat=-25.7479, destination_lon=28.2293,
                donation_size=4000, donation_need="Water"
            ),
            Donation(
                origin_lat=-33.9249, origin_lon=18.4241,
                destination_lat=-30.5595, destination_lon=22.9375,
                donation_size=6000, donation_need="Clothing"
            ),
            Donation(
                origin_lat=-33.9249, origin_lon=18.4241,
                destination_lat=-28.4793, destination_lon=24.6727,
                donation_size=2000, donation_need="Shelter"
            )
        ]
        for donation in donation_samples:
            db.session.add(donation)

        # Seed resource routes
        resource_routes_samples = [
            ResourceRoute(
                origin_lat=-26.2041, origin_lon=28.0473,
                destination_lat=-25.7479, destination_lon=28.2293,
                resource_type="Medical",
                supply_quantity=100
            ),
            ResourceRoute(
                origin_lat=-26.2041, origin_lon=28.0473,
                destination_lat=-29.8587, destination_lon=31.0218,
                resource_type="Food",
                supply_quantity=250
            ),
            ResourceRoute(
                origin_lat=-26.2041, origin_lon=28.0473,
                destination_lat=-30.5595, destination_lon=22.9375,
                resource_type="Shelter",
                supply_quantity=50
            )
        ]
        for route in resource_routes_samples:
            db.session.add(route)

        # Seed a sample child location
        child_location_sample = ChildLocation(
            lat=-33.9608,
            lon=25.6022,
            name="Child A Location"
        )
        db.session.add(child_location_sample)

        # Seed child profiles
        child_profiles_samples = [
            ChildProfile(
                name="Alice", age=7,
                health_status="Stable", priority="High",
                notes="Requires immediate medical attention and regular check-ups."
            ),
            ChildProfile(
                name="Bob", age=9,
                health_status="Under Observation", priority="Medium",
                notes="Regular follow-up needed."
            ),
            ChildProfile(
                name="Charlie", age=6,
                health_status="Healthy", priority="Low",
                notes="Routine monitoring advised."
            )
        ]
        for profile in child_profiles_samples:
            db.session.add(profile)

        # Seed sample users
        sample_users = [
            {"username": "agent1", "password": "test123", "role": "field_agent"},
            {"username": "donor1", "password": "test123", "role": "donor"},
            {"username": "care1", "password": "test123", "role": "child_care"},
            {"username": "manager1", "password": "test123", "role": "mission_manager"}
        ]
        for u in sample_users:
            user = User(username=u["username"], role=u["role"])
            user.set_password(u["password"])
            db.session.add(user)

        db.session.commit()
        print("Initialized the database with sample donation data, resource routes, child location, child profiles, and users.")
