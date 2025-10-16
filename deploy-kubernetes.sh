#!/bin/bash

echo "Starting Minikube deployment for CAMB KVStore..."

# Start Minikube
echo "1. Starting Minikube..."
minikube start --cpus=4 --memory=8192 --driver=docker

# Enable addons
echo "2. Enabling Minikube addons..."
minikube addons enable ingress
minikube addons enable metrics-server

# Build Docker images in Minikube
echo "3. Building Docker images..."
eval $(minikube docker-env)
docker build -t camb-kvstore:latest -f Dockerfile .
docker build -t camb-kvstore-huey:latest -f Dockerfile.huey .

# Create namespace
echo "4. Creating namespace..."
kubectl apply -f kubernetes/00-namespace.yaml

# Apply configurations
echo "5. Applying ConfigMap and Secret..."
kubectl apply -f kubernetes/01-configmap.yaml
kubectl apply -f kubernetes/02-secret.yaml

# Deploy Redis
echo "6. Deploying Redis..."
kubectl apply -f kubernetes/redis/

# Wait for Redis to be ready
echo "7. Waiting for Redis to be ready..."
kubectl wait --for=condition=ready pod -l app=redis,role=master -n camb-kvstore --timeout=300s

# Deploy Application
echo "8. Deploying Application..."
kubectl apply -f kubernetes/app/

# Wait for application to be ready
echo "9. Waiting for application pods to be ready..."
kubectl wait --for=condition=ready pod -l app=camb-kvstore,component=api -n camb-kvstore --timeout=300s

# Deploy Ingress
echo "10. Deploying Ingress..."
kubectl apply -f kubernetes/13-ingress.yaml

# Get Minikube IP
MINIKUBE_IP=$(minikube ip)

echo ""
echo "============================================"
echo "Deployment completed successfully!"
echo "============================================"
echo ""
echo "Access the application at:"
echo "  http://$MINIKUBE_IP:30080"
echo ""
echo "Add to /etc/hosts (optional):"
echo "  $MINIKUBE_IP camb-kvstore.local"
echo ""
echo "Useful commands:"
echo "  kubectl get pods -n camb-kvstore"
echo "  kubectl get svc -n camb-kvstore"
echo "  kubectl logs -f deployment/camb-kvstore-app -n camb-kvstore"
echo "  minikube dashboard"
echo ""