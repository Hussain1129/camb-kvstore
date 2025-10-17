#!/bin/bash

echo "Verifying CAMB KVStore deployment..."
echo ""

echo "1. Checking namespace..."
kubectl get namespace camb-kvstore

echo ""
echo "2. Checking pods..."
kubectl get pods -n camb-kvstore

echo ""
echo "3. Checking services..."
kubectl get svc -n camb-kvstore

echo ""
echo "4. Checking HPA..."
kubectl get hpa -n camb-kvstore

echo ""
echo "5. Checking ingress..."
kubectl get ingress -n camb-kvstore

echo ""
echo "6. Application URL:"
minikube service camb-kvstore-service -n camb-kvstore --url

echo ""
echo "Deployment verification completed!"