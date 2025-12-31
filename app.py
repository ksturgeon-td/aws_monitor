"""AWS Resource Monitor Dashboard - Main Streamlit Application."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from config.settings import settings
from services.resource_aggregator import resource_aggregator
from aws_clients.region_manager import region_manager
from aws_clients.cost_explorer_client import CostExplorerClient

# Configure Streamlit page
st.set_page_config(
    page_title=settings.PAGE_TITLE,
    page_icon=settings.PAGE_ICON,
    layout=settings.LAYOUT
)


@st.cache_data(ttl=settings.RESOURCE_CACHE_TTL)
def fetch_resources(selected_regions=None):
    """Fetch all AWS resources with caching."""
    return resource_aggregator.fetch_all_resources(regions=selected_regions)


@st.cache_data(ttl=settings.COST_CACHE_TTL)
def fetch_cost_data():
    """Fetch cost data with longer caching (Cost Explorer has strict limits)."""
    try:
        cost_client = CostExplorerClient()
        return cost_client.get_cost_and_usage()
    except Exception as e:
        st.warning(f"Could not fetch cost data: {e}")
        return None


def main():
    """Main dashboard application."""

    # Header
    st.title(f"{settings.PAGE_ICON} {settings.PAGE_TITLE}")

    # Last updated timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    col1, col2 = st.columns([6, 1])
    with col1:
        st.caption(f"Last Updated: {current_time}")
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # Sidebar for filters
    with st.sidebar:
        st.header("⚙️ Configuration")

        st.subheader("📍 Region Filter")
        try:
            all_regions = region_manager.get_enabled_regions()
            selected_regions = st.multiselect(
                "Select regions to monitor",
                options=all_regions,
                # default=all_regions[:3] if len(all_regions) > 3 else all_regions,
                default=['us-west-2', 'us-east-1', 'us-east-2'] if len(all_regions) > 3 else all_regions,
                help="Select specific regions or leave all selected for full monitoring"
            )
        except Exception as e:
            st.error(f"Error loading regions: {e}")
            selected_regions = None

        st.subheader("🔧 Service Filter")
        show_ec2 = st.checkbox("EC2 Instances", value=True)
        show_s3 = st.checkbox("S3 Buckets", value=True)
        show_glue = st.checkbox("Glue Databases", value=True)
        show_sagemaker = st.checkbox("SageMaker", value=True)
        show_costs = st.checkbox("Cost Explorer", value=True)

        st.divider()

        st.subheader("⚙️ Settings")
        st.text(f"Resource Cache: {settings.RESOURCE_CACHE_TTL}s")
        st.text(f"Cost Cache: {settings.COST_CACHE_TTL}s")
        st.text(f"Default Region: {settings.AWS_DEFAULT_REGION}")

    # Fetch Resources
    st.header("📊 Resource Summary")

    if not selected_regions:
        st.warning("Please select at least one region to monitor")
        return

    with st.spinner("Fetching AWS resources..."):
        try:
            resources = fetch_resources(selected_regions=tuple(selected_regions))
            summary = resource_aggregator.get_resource_summary(resources)
        except Exception as e:
            st.error(f"Error fetching resources: {e}")
            st.info("Please check your AWS credentials and permissions")
            return

    # Summary Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        ec2_summary = summary.get('ec2', {})
        st.metric(
            label="EC2 Instances",
            value=ec2_summary.get('total_instances', 0),
            delta=f"{ec2_summary.get('running_instances', 0)} running",
            help="Total EC2 instances across selected regions"
        )

    with col2:
        s3_summary = summary.get('s3', {})
        st.metric(
            label="S3 Buckets",
            value=s3_summary.get('total_buckets', 0),
            delta=f"{s3_summary.get('total_size_gb', 0):.2f} GB",
            help="Total S3 buckets and storage size"
        )

    with col3:
        glue_summary = summary.get('glue', {})
        st.metric(
            label="Glue Databases",
            value=glue_summary.get('total_databases', 0),
            delta=f"{glue_summary.get('total_tables', 0)} tables",
            help="Total Glue databases and tables"
        )

    with col4:
        sagemaker_summary = summary.get('sagemaker', {})
        st.metric(
            label="SageMaker",
            value=sagemaker_summary.get('total_notebooks', 0),
            delta=f"{sagemaker_summary.get('active_notebooks', 0)} active",
            help="Total SageMaker notebook instances"
        )

    st.divider()

    # Cost Overview Section
    st.header("💰 Cost Overview")

    if show_costs:
        with st.spinner("Fetching cost data..."):
            cost_data = fetch_cost_data()

        if cost_data:
            cost_col1, cost_col2, cost_col3, cost_col4 = st.columns(4)

            with cost_col1:
                st.metric(
                    label="MTD Spend",
                    value=f"${cost_data['mtd_cost']:,.2f}",
                    help="Month-to-date spending"
                )

            with cost_col2:
                st.metric(
                    label="Projected EOM",
                    value=f"${cost_data['projected_eom_cost']:,.2f}",
                    help="Projected end-of-month cost"
                )

            with cost_col3:
                st.metric(
                    label="Daily Average",
                    value=f"${cost_data['daily_average']:,.2f}",
                    help="Average daily cost"
                )

            with cost_col4:
                st.metric(
                    label="Yesterday",
                    value=f"${cost_data['yesterday_cost']:,.2f}",
                    help="Previous day's cost"
                )

            # Cost Trend Chart
            if cost_data['daily_costs']:
                st.subheader("📈 Cost Trend (Last 30 Days)")

                df_daily = pd.DataFrame(cost_data['daily_costs'])
                fig_trend = px.line(
                    df_daily,
                    x='date',
                    y='cost',
                    title='Daily Cost Trend',
                    labels={'date': 'Date', 'cost': 'Cost ($)'}
                )
                fig_trend.update_traces(line_color='#1f77b4', line_width=2)
                fig_trend.update_layout(hovermode='x unified')
                st.plotly_chart(fig_trend, use_container_width=True)

            # Service Cost Breakdown
            if cost_data['service_costs']:
                st.subheader("🔧 Cost by Service (MTD)")

                df_services = pd.DataFrame(cost_data['service_costs'][:10])  # Top 10 services
                fig_services = px.bar(
                    df_services,
                    x='cost',
                    y='service',
                    orientation='h',
                    title='Top 10 Services by Cost',
                    labels={'cost': 'Cost ($)', 'service': 'Service'}
                )
                fig_services.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_services, use_container_width=True)
        else:
            st.info("💡 Cost data unavailable. Ensure Cost Explorer is enabled and you have the necessary IAM permissions.")
    else:
        st.info("Cost monitoring is disabled. Enable it in the sidebar to view cost data.")

    st.divider()

    # Detailed Resources Section
    st.header("📋 Detailed Resources")

    # Create tabs for each service
    tab1, tab2, tab3, tab4 = st.tabs(["EC2 Instances", "S3 Buckets", "Glue Databases", "SageMaker"])

    with tab1:
        if show_ec2:
            ec2_data = resources.get('ec2', {})
            instances = ec2_data.get('instances', [])

            if instances:
                st.subheader(f"EC2 Instances ({len(instances)} total)")

                # Convert to DataFrame for better display
                df = pd.DataFrame(instances)

                # Reorder columns for better readability
                columns_order = ['name', 'instance_id', 'instance_type', 'state',
                               'region', 'availability_zone', 'private_ip', 'public_ip',
                               'launch_time']
                df = df[[col for col in columns_order if col in df.columns]]

                # Display with filters
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "state": st.column_config.TextColumn(
                            "State",
                            help="Instance state"
                        ),
                        "instance_type": st.column_config.TextColumn(
                            "Type",
                            help="Instance type"
                        )
                    }
                )

                # Show errors if any
                errors = ec2_data.get('errors', [])
                if errors:
                    with st.expander(f"⚠️ Errors ({len(errors)})"):
                        for error in errors:
                            st.error(f"Region {error['region']}: {error['error']}")
            else:
                st.info("No EC2 instances found in selected regions")
        else:
            st.info("EC2 monitoring is disabled. Enable it in the sidebar.")

    with tab2:
        if show_s3:
            s3_data = resources.get('s3', {})
            buckets = s3_data.get('buckets', [])

            if buckets:
                st.subheader(f"S3 Buckets ({len(buckets)} total)")

                # Convert to DataFrame
                df = pd.DataFrame(buckets)

                # Display
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "size_gb": st.column_config.NumberColumn(
                            "Size (GB)",
                            help="Bucket size in GB",
                            format="%.2f"
                        ),
                        "object_count": st.column_config.NumberColumn(
                            "Objects",
                            help="Number of objects",
                            format="%d"
                        )
                    }
                )

                # Show error if any
                if 'error' in s3_data:
                    st.error(f"Error: {s3_data['error']}")
            else:
                st.info("No S3 buckets found")
        else:
            st.info("S3 monitoring is disabled. Enable it in the sidebar.")

    with tab3:
        if show_glue:
            glue_data = resources.get('glue', {})
            databases = glue_data.get('databases', [])

            if databases:
                st.subheader(f"Glue Databases ({len(databases)} total)")

                # Create expandable sections for each database
                for db in databases:
                    with st.expander(f"📂 {db['name']} ({db['table_count']} tables)"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.text(f"Description: {db['description']}")
                            st.text(f"Location: {db['location']}")
                        with col2:
                            st.text(f"Region: {db['region']}")
                            st.text(f"Created: {db['create_time']}")

                        # Show tables if any
                        if db.get('tables'):
                            st.markdown("**Tables:**")
                            tables_df = pd.DataFrame(db['tables'])
                            if 'parameters' in tables_df.columns:
                                tables_df = tables_df.drop('parameters', axis=1)
                            st.dataframe(tables_df, use_container_width=True, hide_index=True)

                # Show errors if any
                errors = glue_data.get('errors', [])
                if errors:
                    with st.expander(f"⚠️ Errors ({len(errors)})"):
                        for error in errors:
                            st.error(f"Region {error['region']}: {error['error']}")
            else:
                st.info("No Glue databases found in selected regions")
        else:
            st.info("Glue monitoring is disabled. Enable it in the sidebar.")

    with tab4:
        if show_sagemaker:
            sagemaker_data = resources.get('sagemaker', {})

            # Notebook Instances
            notebooks = sagemaker_data.get('notebook_instances', [])
            if notebooks:
                st.subheader(f"Notebook Instances ({len(notebooks)} total)")
                df_notebooks = pd.DataFrame(notebooks)
                st.dataframe(df_notebooks, use_container_width=True, hide_index=True)

            # Endpoints
            endpoints = sagemaker_data.get('endpoints', [])
            if endpoints:
                st.subheader(f"Endpoints ({len(endpoints)} total)")
                df_endpoints = pd.DataFrame(endpoints)
                st.dataframe(df_endpoints, use_container_width=True, hide_index=True)

            # Training Jobs
            training_jobs = sagemaker_data.get('training_jobs', [])
            if training_jobs:
                st.subheader(f"Recent Training Jobs ({len(training_jobs)} total)")
                df_training = pd.DataFrame(training_jobs)
                st.dataframe(df_training, use_container_width=True, hide_index=True)

            if not notebooks and not endpoints and not training_jobs:
                st.info("No SageMaker resources found in selected regions")

            # Show errors if any
            errors = sagemaker_data.get('errors', [])
            if errors:
                with st.expander(f"⚠️ Errors ({len(errors)})"):
                    for error in errors:
                        st.error(f"Region {error['region']}: {error['error']}")
        else:
            st.info("SageMaker monitoring is disabled. Enable it in the sidebar.")

    # Footer
    st.divider()
    st.caption(
        "AWS Resource Monitor Dashboard | "
        "Data refreshes automatically based on cache TTL settings"
    )


if __name__ == "__main__": 
    main()
