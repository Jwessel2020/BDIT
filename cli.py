# cli.py
import os
from app import app, db
from models import Donation, User, ResourceRoute, ChildLocation, ChildProfile, Project, Message, FieldAgentLocation
from datetime import datetime, timedelta
import random

@app.cli.command('initdb')
def initdb():
    """
    Initializes the database and seeds it with sample data including users, projects,
    donations, resource routes, child locations, and child profiles.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Seed sample users
        sample_users = [
            {"username": "agent1", "password": "test123", "role": "field_agent"},
            {"username": "donor1", "password": "test123", "role": "donor"},
            {"username": "care1", "password": "test123", "role": "child_care"},
            {"username": "manager1", "password": "test123", "role": "mission_manager"},
            {"username": "manager2", "password": "test123", "role": "mission_manager"}
        ]
        users = {}
        for u_data in sample_users:
            user = User(username=u_data["username"], role=u_data["role"])
            user.set_password(u_data["password"])
            db.session.add(user)
            users[u_data["username"]] = user
        db.session.commit() # Commit users to get their IDs

        # Seed sample projects
        project_samples = [
            Project(
                name="Cape Town Child Vaccination Drive",
                description="A project to vaccinate children under 5 in vulnerable Cape Town communities.",
                manager_id=users['manager1'].id,
                budget=50000.00,
                start_date=datetime.utcnow() - timedelta(days=30),
                status='Ongoing',
                goal_description='Achieve 90% vaccination rate for registered children.',
                goal_target_value=90,
                goal_current_value=65,
                goal_unit='%'
            ),
            Project(
                name="Durban Food Security Program",
                description="Distribution of essential food packages to families in need in Durban.",
                manager_id=users['manager1'].id,
                budget=75000.00,
                start_date=datetime.utcnow() - timedelta(days=10),
                status='Ongoing',
                goal_description='Distribute 5000 food packages.',
                goal_target_value=5000,
                goal_current_value=1200,
                goal_unit='packages'
            ),
            Project(
                name="Johannesburg Shelter Refurbishment",
                description="Refurbishing temporary shelters for displaced families in Johannesburg.",
                manager_id=users['manager2'].id,
                budget=120000.00,
                start_date=datetime.utcnow() - timedelta(days=60),
                end_date=datetime.utcnow() - timedelta(days=5), # Recently completed
                status='Completed',
                goal_description='Refurbish 3 shelter facilities.',
                goal_target_value=3,
                goal_current_value=3,
                goal_unit='facilities'
            ),
            Project(
                name="Pretoria Education Support",
                description="Providing educational materials and support to underprivileged schools.",
                manager_id=users['manager2'].id,
                budget=30000.00,
                start_date=datetime.utcnow() + timedelta(days=15), # Starts in the future
                status='Planning',
                goal_description='Equip 10 schools with new textbooks.',
                goal_target_value=10,
                goal_current_value=0,
                goal_unit='schools'
            )
        ]
        projects = {}
        for p_data in project_samples:
            db.session.add(p_data)
            projects[p_data.name] = p_data
        db.session.commit() # Commit projects to get their IDs

        # Seed donation data, some linked to projects
        donation_samples = [
            Donation(
                origin_lat=-33.9249, origin_lon=18.4241, # Cape Town
                destination_lat=-33.9200, destination_lon=18.4300, # Near Cape Town project area
                donation_size=5000, donation_need="Vaccines",
                project_id=projects["Cape Town Child Vaccination Drive"].id
            ),
            Donation(
                origin_lat=-25.7479, origin_lon=28.2293, # Pretoria
                destination_lat=-29.8587, destination_lon=31.0218, # Durban
                donation_size=3000, donation_need="Food Supplies",
                project_id=projects["Durban Food Security Program"].id
            ),
            Donation(
                origin_lat=-26.2041, origin_lon=28.0473, # Johannesburg
                destination_lat=-26.1900, destination_lon=28.0300, # Near Johannesburg project area
                donation_size=10000, donation_need="Building Materials",
                project_id=projects["Johannesburg Shelter Refurbishment"].id
            ),
            Donation( # Unassigned donation
                origin_lat=-33.9249, origin_lon=18.4241,
                destination_lat=-25.7479, destination_lon=28.2293,
                donation_size=4000, donation_need="General Aid"
            )
        ]
        for donation in donation_samples:
            db.session.add(donation)

        # Seed resource routes, some linked to projects
        resource_routes_samples = [
            ResourceRoute(
                origin_lat=-33.9000, origin_lon=18.4000, # Cape Town Depot
                destination_lat=-33.9200, destination_lon=18.4300, # CT Project Site 1
                resource_type="Medical", supply_quantity=100,
                project_id=projects["Cape Town Child Vaccination Drive"].id
            ),
            ResourceRoute(
                origin_lat=-29.8000, origin_lon=31.0000, # Durban Warehouse
                destination_lat=-29.8587, destination_lon=31.0218, # Durban Project Site
                resource_type="Food", supply_quantity=250,
                project_id=projects["Durban Food Security Program"].id
            ),
            ResourceRoute( # Unassigned route
                origin_lat=-26.2041, origin_lon=28.0473,
                destination_lat=-25.7479, destination_lon=28.2293,
                resource_type="Shelter", supply_quantity=50
            )
        ]
        for route in resource_routes_samples:
            db.session.add(route)

        # Seed child profiles, some linked to projects and with locations
        child_profiles_samples = [
            ChildProfile(
                name="Alice Mbatha", age=4, health_status="Needs Vaccination", priority="High",
                notes="Part of Cape Town Vaccination Drive.", current_lat=-33.9210, current_lon=18.4310,
                project_id=projects["Cape Town Child Vaccination Drive"].id
            ),
            ChildProfile(
                name="Bob Zulu", age=3, health_status="Healthy", priority="Low",
                notes="Scheduled for checkup.", current_lat=-33.9250, current_lon=18.4290,
                project_id=projects["Cape Town Child Vaccination Drive"].id
            ),
            ChildProfile(
                name="Charlie Pillay", age=7, health_status="Under Observation", priority="Medium",
                notes="Receiving food aid in Durban.", current_lat=-29.8590, current_lon=31.0220,
                project_id=projects["Durban Food Security Program"].id
            ),
            ChildProfile( # Unassigned child profile
                name="David Smith", age=6, health_status="Stable", priority="Low",
                notes="Awaiting project assignment.", current_lat=-26.2000, current_lon=28.0400
            )
        ]
        for profile in child_profiles_samples:
            db.session.add(profile)
        
        # Seed Field Agent Locations, some linked to projects
        field_agent_locations_samples = [
            FieldAgentLocation(user_id=users['agent1'].id, lat=-33.9220, lon=18.4320, timestamp=datetime.utcnow() - timedelta(hours=1), project_id=projects["Cape Town Child Vaccination Drive"].id),
            FieldAgentLocation(user_id=users['agent1'].id, lat=-29.8580, lon=31.0210, timestamp=datetime.utcnow() - timedelta(hours=2), project_id=projects["Durban Food Security Program"].id),
            FieldAgentLocation(user_id=users['agent1'].id, lat=-26.1950, lon=28.0350, timestamp=datetime.utcnow() - timedelta(hours=3)) # General location ping
        ]
        for fal_data in field_agent_locations_samples:
            db.session.add(fal_data)

        db.session.commit()
        print("Initialized the database with sample data including users, projects, donations, resource routes, child profiles, and field agent locations.")
