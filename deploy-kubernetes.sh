#!/bin/bash

echo "Starting Minikube deployment for CAMB KVStore..."

echo "Checking Minikube..."

if minikube status | grep -q "host: Running"; then
    echo "✅ Minikube is running."
else
    echo "❌ Minikube is not running. Starting it now..."
    minikube start
fi


echo "Starting Minikube..."
minikube start --cpus=4 --memory=8192 --driver=docker

echo "Enabling Minikube addons..."
minikube addons enable ingress
minikube addons enable metrics-server

echo "Creating namespace..."
kubectl apply -f kubernetes/namespace.yaml

echo "Applying ConfigMap and Secret..."
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secret.yaml

echo "Deploying Redis..."
kubectl apply -f kubernetes/redis/

echo "Deploying Application..."
kubectl apply -f kubernetes/app/

echo "Deploying Ingress..."
kubectl apply -f kubernetes/ingress.yaml

MINIKUBE_IP=$(minikube ip)

echo ""
echo "============================================"
echo "Deployment completed successfully!"
echo "============================================"
echo ""
echo "Run minikube command to access your project on localhost"
minikube service camb-kvstore-service -n camb-kvstore


echo "Useful commands:"
echo "  kubectl get pods -n camb-kvstore"
echo "  kubectl get deployments -n camb-kvstore"
echo "  kubectl get svc -n camb-kvstore"
echo "  kubectl get ns -n camb-kvstore"
echo "  kubectl logs -f deployment/camb-kvstore-app -n camb-kvstore"
echo "  minikube dashboard"
echo ""