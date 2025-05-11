# cli.py
import os
from app import app, db
from models import Donation, User, ResourceRoute, ChildLocation, ChildProfile, Project, Message, FieldAgentLocation, Crisis
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
            {"username": "donor2", "password": "test123", "role": "donor"},
            {"username": "donor3", "password": "test123", "role": "donor"},
            {"username": "donor_high_value", "password": "test123", "role": "donor"},
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

        # Seed Sample Crises
        crisis_samples = [
            Crisis(
                name="Northern Region Floods - Winter 2024",
                description="Severe flooding affecting multiple villages in the Northern Region, displacing hundreds.",
                location_lat=-23.5000, location_lon=29.0000, # Example coordinates
                start_date=datetime.utcnow() - timedelta(days=10),
                status="Active"
            ),
            Crisis(
                name="Eastern Province Drought Watch",
                description="Ongoing drought conditions leading to food and water shortages.",
                location_lat=-25.0000, location_lon=31.5000,
                start_date=datetime.utcnow() - timedelta(days=45),
                status="Monitoring"
            )
        ]
        for crisis_data in crisis_samples:
            db.session.add(crisis_data)
        db.session.commit()
        crises_dict = {c.name: c for c in Crisis.query.all()} # For easy lookup

        # Seed donation data, some linked to projects
        donation_samples = []
        donor1 = users['donor1']
        donor2 = users['donor2']
        donor3 = users['donor3']
        donor_high_value = users['donor_high_value']
        all_donor_users = [donor1, donor2, donor3, donor_high_value]

        # Project 1: Cape Town Child Vaccination Drive
        ct_project = projects_dict["Cape Town Child Vaccination Drive"]
        for i in range(random.randint(3, 6)):
            chosen_donor = random.choice(all_donor_users + [None]) # Allow some anonymous
            donation_samples.append(Donation(
                origin_lat=-33.9249, origin_lon=18.4241, 
                destination_lat=-33.9200, destination_lon=18.4300, 
                donation_size=random.uniform(100, (5000 if chosen_donor != donor_high_value else 15000)),
                donation_need=random.choice(["Vaccines", "Medical Kits", "Logistics"]),
                project_id=ct_project.id,
                timestamp=ct_project.start_date + timedelta(days=random.randint(1, 25)),
                donor_id=chosen_donor.id if chosen_donor else None
            ))
        
        # Project 2: Durban Food Security Program
        dbn_project = projects_dict["Durban Food Security Program"]
        for i in range(random.randint(3, 7)):
            chosen_donor = random.choice(all_donor_users + [None])
            donation_samples.append(Donation(
                origin_lat=-25.7479, origin_lon=28.2293, 
                destination_lat=-29.8587, destination_lon=31.0218, 
                donation_size=random.uniform(200, (6000 if chosen_donor != donor_high_value else 20000)),
                donation_need=random.choice(["Food Packages", "Clean Water", "Distribution Costs"]),
                project_id=dbn_project.id,
                timestamp=dbn_project.start_date + timedelta(days=random.randint(1, 20)),
                donor_id=chosen_donor.id if chosen_donor else None
            ))

        # Project 3: Johannesburg Shelter Refurbishment
        jhb_project = projects_dict["Johannesburg Shelter Refurbishment"]
        for i in range(random.randint(2, 5)):
            chosen_donor = random.choice(all_donor_users + [None])
            donation_ts = jhb_project.start_date + timedelta(days=random.randint(1, 50))
            if jhb_project.end_date and donation_ts >= jhb_project.end_date:
                donation_ts = jhb_project.end_date - timedelta(days=1)
            donation_samples.append(Donation(
                origin_lat=-26.2041, origin_lon=28.0473, 
                destination_lat=-26.1900, destination_lon=28.0300,
                donation_size=random.uniform(500, (10000 if chosen_donor != donor_high_value else 25000)),
                donation_need=random.choice(["Building Materials", "Furniture", "Utilities Setup"]),
                project_id=jhb_project.id,
                timestamp=donation_ts,
                donor_id=chosen_donor.id if chosen_donor else None
            ))
        
        # Project 4: Pretoria Education Support (Planning phase, fewer donations, maybe from specific donors)
        pta_project = projects_dict["Pretoria Education Support"]
        for i in range(random.randint(1, 3)): # Fewer donations for a planning phase project
            chosen_donor = random.choice([donor1, donor_high_value, None]) # More targeted donors for planning phase
            donation_samples.append(Donation(
                origin_lat=-25.7461, origin_lon=28.1881, # Pretoria coords
                destination_lat=-25.7479, destination_lon=28.2293, # Near Pretoria
                donation_size=random.uniform(50, (2000 if chosen_donor != donor_high_value else 5000)),
                donation_need="Seed Funding",
                project_id=pta_project.id,
                timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 5)), # Recent seed donations
                donor_id=chosen_donor.id if chosen_donor else None
            ))

        # Unassigned/General Aid donations from various donors
        for i in range(random.randint(5, 10)): # More general aid donations
            chosen_donor = random.choice(all_donor_users + [None])
            donation_samples.append(Donation(
                origin_lat=random.uniform(-34, -25), origin_lon=random.uniform(18, 30),
                destination_lat=random.uniform(-34, -25), destination_lon=random.uniform(18, 30),
                donation_size=random.uniform(50, (3000 if chosen_donor != donor_high_value else 10000)), 
                donation_need="General Operational Support",
                timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 150)),
                donor_id=chosen_donor.id if chosen_donor else None,
                project_id=None # Explicitly no project for general aid
            ))

        for donation in donation_samples:
            db.session.add(donation)

        # Seed resource routes, linking some to crises and agents
        resource_routes_samples = [
            ResourceRoute(
                origin_lat=-33.9000, origin_lon=18.4000, 
                destination_lat=-33.9200, destination_lon=18.4300, 
                resource_type="Medical", supply_quantity=100,
                project_id=projects_dict["Cape Town Child Vaccination Drive"].id,
                status="Delivered", 
                assigned_agent_id=users['agent1'].id
            ),
            ResourceRoute(
                origin_lat=-29.8000, origin_lon=31.0000, 
                destination_lat=-29.8587, destination_lon=31.0218, 
                resource_type="Food", supply_quantity=250,
                project_id=projects_dict["Durban Food Security Program"].id,
                status="In Transit", 
                assigned_agent_id=users['agent1'].id,
                target_crisis_id=crises_dict.get("Eastern Province Drought Watch").id if crises_dict.get("Eastern Province Drought Watch") else None
            ),
            ResourceRoute( 
                origin_lat=-26.2041, origin_lon=28.0473,
                destination_lat=-25.7479, destination_lon=28.2293,
                resource_type="Shelter Kits", supply_quantity=75,
                status="Allocated",
                target_crisis_id=crises_dict.get("Northern Region Floods - Winter 2024").id if crises_dict.get("Northern Region Floods - Winter 2024") else None
            )
        ]
        for route in resource_routes_samples:
            db.session.add(route)

        # Seed child profiles, linking some to crises and adding new fields
        child_profiles_samples = [
            ChildProfile(
                name="Alice Mbatha", age=4, health_status="Needs Vaccination", priority="High",
                notes="Part of Cape Town Vaccination Drive.", current_lat=-33.9210, current_lon=18.4310,
                project_id=projects_dict["Cape Town Child Vaccination Drive"].id,
                urgency_score=8, last_welfare_check_date=datetime.utcnow() - timedelta(days=3)
            ),
            ChildProfile(
                name="Bob Zulu", age=3, health_status="Healthy", priority="Low",
                notes="Scheduled for checkup.", current_lat=-33.9250, current_lon=18.4290,
                project_id=projects_dict["Cape Town Child Vaccination Drive"].id,
                urgency_score=3, last_welfare_check_date=datetime.utcnow() - timedelta(days=10)
            ),
            ChildProfile(
                name="Charlie Pillay", age=7, health_status="Under Observation", priority="Medium",
                notes="Affected by drought, receiving food aid.", current_lat=-25.0100, current_lon=31.5100,
                project_id=projects_dict["Durban Food Security Program"].id, # May also be linked to a project
                urgency_score=6, last_welfare_check_date=datetime.utcnow() - timedelta(days=5),
                assigned_crisis_id=crises_dict.get("Eastern Province Drought Watch").id if crises_dict.get("Eastern Province Drought Watch") else None
            ),
            ChildProfile( 
                name="David Smith", age=6, health_status="Stable", priority="Low",
                notes="Displaced by floods.", current_lat=-23.5050, current_lon=29.0050,
                urgency_score=7, last_welfare_check_date=datetime.utcnow() - timedelta(days=2),
                assigned_crisis_id=crises_dict.get("Northern Region Floods - Winter 2024").id if crises_dict.get("Northern Region Floods - Winter 2024") else None
            ),
            ChildProfile( 
                name="Eva Nkosi", age=1, health_status="Critical", priority="High",
                notes="Needs urgent medical attention due to flood-related illness.", current_lat=-23.5100, current_lon=29.0100,
                urgency_score=10, last_welfare_check_date=datetime.utcnow() - timedelta(days=1),
                assigned_crisis_id=crises_dict.get("Northern Region Floods - Winter 2024").id if crises_dict.get("Northern Region Floods - Winter 2024") else None
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
