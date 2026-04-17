from ultralytics import YOLO

model=YOLO('best.pt')
print('Model loaded successfully')

print(f'\nModel: {model.model_name}\n')
print(f'class names: {model.names}\n')
print(f'number of classes: {model.nc}\n')    

print('\n Model is ready for testing')