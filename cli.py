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
                budget=random.uniform(30000, 80000),
                start_date=datetime.utcnow() - timedelta(days=random.randint(20, 60)),
                status='Ongoing',
                goal_description='Achieve 90% vaccination rate for registered children.',
                goal_target_value=90,
                goal_current_value=random.randint(40, 85),
                goal_unit='%'
            ),
            Project(
                name="Durban Food Security Program",
                description="Distribution of essential food packages to families in need in Durban.",
                manager_id=users['manager1'].id,
                budget=random.uniform(50000, 120000),
                start_date=datetime.utcnow() - timedelta(days=random.randint(5, 45)),
                status='Ongoing',
                goal_description='Distribute 5000 food packages.',
                goal_target_value=5000,
                goal_current_value=random.randint(500, 4500),
                goal_unit='packages'
            ),
            Project(
                name="Johannesburg Shelter Refurbishment",
                description="Refurbishing temporary shelters for displaced families in Johannesburg.",
                manager_id=users['manager2'].id,
                budget=random.uniform(80000, 150000),
                start_date=datetime.utcnow() - timedelta(days=random.randint(60, 120)),
                end_date=datetime.utcnow() - timedelta(days=random.randint(1, 30)), # Recently completed
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
                budget=random.uniform(20000, 60000),
                start_date=datetime.utcnow() + timedelta(days=random.randint(10, 30)), # Starts in the future
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
        db.session.commit() # Commit projects to get their IDs
        # Re-fetch projects to ensure IDs are populated and accessible
        projects_dict = {p.name: p for p in Project.query.all()}

        # Seed donation data, some linked to projects
        donation_samples = []
        donor1_user = users['donor1']

        # Project 1: Cape Town Child Vaccination Drive - Donations from donor1 and others
        for i in range(random.randint(2, 4)):
            donation_samples.append(Donation(
                origin_lat=-33.9249, origin_lon=18.4241, 
                destination_lat=-33.9200, destination_lon=18.4300, 
                donation_size=random.uniform(500, 5000),
                donation_need=random.choice(["Vaccines", "Medical Kits", "Logistics"]),
                project_id=projects_dict["Cape Town Child Vaccination Drive"].id,
                timestamp=projects_dict["Cape Town Child Vaccination Drive"].start_date + timedelta(days=random.randint(1, 25)),
                donor_id=donor1_user.id if i % 2 == 0 else None
            ))
        
        # Project 2: Durban Food Security Program - Donations from donor1 and others
        for i in range(random.randint(2, 4)):
            donation_samples.append(Donation(
                origin_lat=-25.7479, origin_lon=28.2293, 
                destination_lat=-29.8587, destination_lon=31.0218, 
                donation_size=random.uniform(1000, 8000),
                donation_need=random.choice(["Food Packages", "Clean Water", "Distribution Costs"]),
                project_id=projects_dict["Durban Food Security Program"].id,
                timestamp=projects_dict["Durban Food Security Program"].start_date + timedelta(days=random.randint(1, 20)),
                donor_id=donor1_user.id if i % 2 == 0 else None
            ))

        # Project 3: Johannesburg Shelter Refurbishment - Donations from others (not donor1 for variety)
        for i in range(random.randint(2, 5)):
            donation_ts = projects_dict["Johannesburg Shelter Refurbishment"].start_date + timedelta(days=random.randint(1, 50))
            if projects_dict["Johannesburg Shelter Refurbishment"].end_date and donation_ts >= projects_dict["Johannesburg Shelter Refurbishment"].end_date:
                donation_ts = projects_dict["Johannesburg Shelter Refurbishment"].end_date - timedelta(days=1)
            donation_samples.append(Donation(
                origin_lat=-26.2041, origin_lon=28.0473, 
                destination_lat=-26.1900, destination_lon=28.0300,
                donation_size=random.uniform(2000, 15000),
                donation_need=random.choice(["Building Materials", "Furniture", "Utilities Setup"]),
                project_id=projects_dict["Johannesburg Shelter Refurbishment"].id,
                timestamp=donation_ts,
                donor_id=None
            ))

        # Unassigned donations (some from donor1, some anonymous)
        for i in range(random.randint(2, 4)):
            donation_samples.append(Donation(
                origin_lat=random.uniform(-34, -25), origin_lon=random.uniform(18, 30),
                destination_lat=random.uniform(-34, -25), destination_lon=random.uniform(18, 30),
                donation_size=random.uniform(100, 10000), 
                donation_need="General Aid",
                timestamp=datetime.utcnow() - timedelta(days=random.randint(5, 100)),
                donor_id=donor1_user.id if i % 2 == 0 else None
            ))

        for donation in donation_samples:
            db.session.add(donation)

        # Seed resource routes, some linked to projects
        resource_routes_samples = [
            ResourceRoute(
                origin_lat=-33.9000, origin_lon=18.4000, # Cape Town Depot
                destination_lat=-33.9200, destination_lon=18.4300, # CT Project Site 1
                resource_type="Medical", supply_quantity=100,
                project_id=projects_dict["Cape Town Child Vaccination Drive"].id
            ),
            ResourceRoute(
                origin_lat=-29.8000, origin_lon=31.0000, # Durban Warehouse
                destination_lat=-29.8587, destination_lon=31.0218, # Durban Project Site
                resource_type="Food", supply_quantity=250,
                project_id=projects_dict["Durban Food Security Program"].id
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
                project_id=projects_dict["Cape Town Child Vaccination Drive"].id
            ),
            ChildProfile(
                name="Bob Zulu", age=3, health_status="Healthy", priority="Low",
                notes="Scheduled for checkup.", current_lat=-33.9250, current_lon=18.4290,
                project_id=projects_dict["Cape Town Child Vaccination Drive"].id
            ),
            ChildProfile(
                name="Charlie Pillay", age=7, health_status="Under Observation", priority="Medium",
                notes="Receiving food aid in Durban.", current_lat=-29.8590, current_lon=31.0220,
                project_id=projects_dict["Durban Food Security Program"].id
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
            FieldAgentLocation(user_id=users['agent1'].id, lat=-33.9220, lon=18.4320, timestamp=datetime.utcnow() - timedelta(hours=1), project_id=projects_dict["Cape Town Child Vaccination Drive"].id),
            FieldAgentLocation(user_id=users['agent1'].id, lat=-29.8580, lon=31.0210, timestamp=datetime.utcnow() - timedelta(hours=2), project_id=projects_dict["Durban Food Security Program"].id),
            FieldAgentLocation(user_id=users['agent1'].id, lat=-26.1950, lon=28.0350, timestamp=datetime.utcnow() - timedelta(hours=3)) # General location ping
        ]
        for fal_data in field_agent_locations_samples:
            db.session.add(fal_data)

        db.session.commit()
        print("Initialized the database with sample data including users, projects, donations, resource routes, child profiles, and field agent locations.")
