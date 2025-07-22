def find_gen3_helm_path():
    # Try relative path first (most common case)
    relative_path = os.path.join(os.path.dirname(__file__), '..', 'gen3-helm')
    if os.path.exists(os.path.join(relative_path, 'helm', 'pcdcanalysistools')):
        return relative_path
    
    # Search in parent directories
    current_dir = os.path.dirname(__file__)
    for _ in range(3):  # Search up to 3 levels up
        current_dir = os.path.dirname(current_dir)
        gen3_helm_candidate = os.path.join(current_dir, 'gen3-helm')
        if os.path.exists(os.path.join(gen3_helm_candidate, 'helm', 'pcdcanalysistools')):
            return gen3_helm_candidate
    
    # Fallback to environment variable or error
    env_path = os.getenv('GEN3_HELM_PATH')
    if env_path and os.path.exists(env_path):
        return env_path
    
    fail("Could not find gen3-helm repository. Please set GEN3_HELM_PATH environment variable.")
    
custom_build(
    'pcdcanalysistools',  # Use localhost prefix for local registry
    'nerdctl --namespace k8s.io build -f Dockerfile.tilt -t $EXPECTED_REF .',  # Use nerdctl for Rancher Desktop
    deps=['./PcdcAnalysisTools', './Dockerfile.tilt'],  # Watch these directories/files for changes
    disable_push=True,  # Don't push to external registry - keep it local
    skips_local_docker=True,  # We are using local docker/nerdctl
    live_update=[
        # Sync local files to the container
        sync('./PcdcAnalysisTools', '/PcdcAnalysisTools/PcdcAnalysisTools'),
        # Restart the Flask server when files change
        run('cd /PcdcAnalysisTools && touch /tmp/restart.txt', trigger=['./PcdcAnalysisTools'])
    ]
)


# Find gen3-helm relative to current directory
gen3_helm_path = find_gen3_helm_path()

local_resource(
    'helm-deps',
    'cd %s/helm/pcdcanalysistools && helm dependency update' % gen3_helm_path,
    deps=[
        '%s/helm/pcdcanalysistools/Chart.yaml' % gen3_helm_path
    ]
)

k8s_yaml(helm(
    '%s/helm/pcdcanalysistools' % gen3_helm_path,
    name='pcdcanalysistools',
    values=['%s/values.yaml' % gen3_helm_path],
    set=[
        "image.repository=pcdcanalysistools",
        "image.pullPolicy=Never"
    ]
))