# SLURM-based HPC Cluster Setup Guide
This guide will help you deploy ServerlessLLM on a SLURM-based HPC (High Performance Computing) cluster. Please make sure you have installed the ServerlessLLM following the [installation guide](https://serverlessllm.github.io/docs/stable/getting_started/installation#installing-with-pip) on all machines.
## Some Tips about Installation
Firstly, **all installation work should be done on the login node**. We recommend using [installing with pip](https://serverlessllm.github.io/docs/stable/getting_started/installation#installing-with-pip) if there is no CUDA driver on login node.
If you want to [install from source](https://serverlessllm.github.io/docs/stable/getting_started/installation#installing-from-source), please make sure CUDA driver available on the login node.
Here are some commands to check it.
```shell
module avail cuda # if you can see some CUDA options, it means CUDA is available, then load the cuda module
module load cuda-12.x # load specific CUDA version
# or
nvidia-smi # if you can see the GPU information, it means CUDA is available
# or
which nvcc # if you can see the CUDA compiler's path, it means CUDA is available
```
However, we **strongly recommend that you read the documentation for the HPC you are using** to find out how to check if the CUDA driver is available.

## Step 1: Start the Head Node
1. **Activate the ``sllm`` environment and start the head node.**

   Here is the example script, named start_head_node.sh.
    ```shell
    #!/bin/bash
    #SBATCH --partition=your_partition # specify the partition you want to use
    #SBATCH --job-name=sllm-head
    #SBATCH --output=sllm_head.out
    #SBATCH --error=sllm_head.err
    #SBATCH --nodes=1
    #SBATCH --ntasks=1
    #SBATCH --cpus-per-task=4
    #SBATCH --gpus-per-task=0

    cd /path/to/ServerlessLLM

    conda activate sllm

    ray start --head --port=6379 --num-cpus=12 --num-gpus=0 \
    --resources='{"control_node": 1}' --block
    ```
   - Read the HPC's documentation to find out which partition you can use. Replace ```your_partition``` in the script with that partition name.
   - Replace ```/path/to/ServerlessLLM``` with the path to the ServerlessLLM installation directory.

2. **Find an idle node**

    Use ```sinfo -p your_partition``` to find some idle nodes. For example:
    ```
   $ sinfo -p compute
   PARTITION AVAIL  NODES  STATE  TIMELIMIT  NODELIST
   compute    up       10  idle   infinite   compute[01-10]
   compute    up        5  alloc  infinite   compute[11-15]
   compute    up        2  down   infinite   compute[16-17]
    ```
3. **Submit the script**

    Use ```sbatch --nodelist=idle01 start_head_node.sh``` to submit the script to certain idle node (here we assume it is ```idle01```).

4. **Expected output**

   In ```sllm_head.out```, you will see the following output:
   ```shell
   Local node IP: xxx.xxx.xx.xx
   --------------------
   Ray runtime started.
   --------------------
   ```
   Remember the IP address, denoted ```<HEAD_NODE_IP>```, you will need it in following steps.

## Step 2: Start the Worker Node
1. **Activate the ```sllm-worker``` environment and start the worker node.**

   Here is the example script, named```start_worker_node.sh```.
   ```shell
   #!/bin/sh
   #SBATCH --partition=your_partition
   #SBATCH --job-name=sllm-worker
   #SBATCH --output=sllm_worker.out
   #SBATCH --error=sllm_worker.err
   #SBATCH --gres=gpu:2                   # Request 2 GPUs
   #SBATCH --cpus-per-task=4              # Request 4 CPU cores
   #SBATCH --mem=16G                      # Request 16GB of RAM

   cd /path/to/ServerlessLLM

   conda activate sllm-worker

   HEAD_NODE_IP=<HEAD_NODE_IP>

   ray start --address=$HEAD_NODE_IP:6379 --num-cpus=4 --num-gpus=2 \
   --resources='{"worker_node": 1, "worker_id_0": 1}' --block
   ```
   - Read the HPC's documentation to find out which partition you can use. Replace ```your_partition``` in the script with that partition name.
   - Replace ```/path/to/ServerlessLLM``` with the path to the ServerlessLLM installation directory.
   - Replace ```<HEAD_NODE_IP>``` with the IP address of the head node.
2. **Submit the script on the other node**

    Use ```sbatch --nodelist=idle02 start_worker_node.sh``` to submit the script to certain idle node (here we assume it is ```idle02```). In addition, We recommend that you place the head and worker on different nodes so that the Store and Serve can start smoothly later, rather than queuing up for resource allocation.
3. **Expected output**

   In ```sllm_worker.out```, you will see the following output:
   ```shell
   Local node IP: xxx.xxx.xx.xx
   --------------------
   Ray runtime started.
   --------------------
   ```

## Step 3: Start the Store on the Worker Node
1. **Activate the ```sllm-worker``` environment and start the store.**

   Here is the example script, named```start_store.sh```.
   ```shell
   #!/bin/sh
   #SBATCH --partition=your_partition
   #SBATCH --gres=gpu:1                   # Request 1 GPU
   #SBATCH --cpus-per-task=4              # Request 4 CPU cores
   #SBATCH --mem=16G                      # Request 16GB of RAM
   #SBATCH --time=01:00:00                # Run time (hh:mm:ss)
   #SBATCH --output=store.log             # Standard output and error log

   cd /path/to/ServerlessLLM

   conda activate sllm-worker

   export CUDA_HOME=/opt/cuda-12.5.0 # replace with your CUDA path
   export PATH=$CUDA_HOME/bin:$PATH
   export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

   sllm-store-server
   ```
   - Read the HPC's documentation to find out which partition you can use. Replace ```your_partition``` in the script with that partition name.
   - Replace ```/path/to/ServerlessLLM``` with the path to the ServerlessLLM installation directory.
   - Replace ```/opt/cuda-12.5.0``` with the path to your CUDA path.
2. **Find the CUDA path**
   - Some slurm-based HPCs have a module system, you can use ```module avail cuda``` to find the CUDA module.
   - If it does not work, read the HPC's documentation carefully to find the CUDA path. For example, my doc said CUDA is in ```\opt```. Then you can use ```srun``` command to start an interactive session on the node, such as ```srun --pty -t 00:30:00 -p your_partition --gres=gpu:1 /bin/bash```. A pseudo-terminal will be started for you to find the path.
   - Find it and replace ```/opt/cuda-12.5.0``` with the path to your CUDA path.
3. **Submit the script on the worker node**

    Use ```sbatch --nodelist=idle02 start_store.sh``` to submit the script to the worker node (```idle02```).
4. **Expected output**

   In ```store.log```, you will see the following output:
   ```shell
   I20241030 11:52:54.719007 1321560 checkpoint_store.cpp:41] Number of GPUs: 1
   I20241030 11:52:54.773468 1321560 checkpoint_store.cpp:43] I/O threads: 4, chunk size: 32MB
   I20241030 11:52:54.773548 1321560 checkpoint_store.cpp:45] Storage path: "./models/"
   I20241030 11:52:55.060559 1321560 checkpoint_store.cpp:71] GPU 0 UUID: 52b01995-4fa9-c8c3-a2f2-a1fda7e46cb2
   I20241030 11:52:55.060798 1321560 pinned_memory_pool.cpp:29] Creating PinnedMemoryPool with 128 buffers of 33554432 bytes
   I20241030 11:52:57.258795 1321560 checkpoint_store.cpp:83] Memory pool created with 4GB
   I20241030 11:52:57.262835 1321560 server.cpp:306] Server listening on 0.0.0.0:8073
   ```
## Step 4: Start the Serve on the Head Node
1. **Check if port 8343 can be accessed**

   - Some HPCs have a firewall that blocks port 8343. You can use ```nc -zv <HEAD_NODE_IP> 8343``` to check if the port is accessible.
   - If it is not accessible, find an available port and replace ```available_port``` in the following script.
2. **Activate the ```sllm``` environment and start the serve.**

   Here is the example script, named```start_serve.sh```.
   ```shell
   #!/bin/sh
   #SBATCH --partition=Teach-Standard
   #SBATCH --gres=gpu:1                   # Request 1 GPU
   #SBATCH --cpus-per-task=4              # Request 4 CPU cores
   #SBATCH --mem=16G                      # Request 16GB of RAM
   #SBATCH --output=serve.log

   cd /path/to/ServerlessLLM

   conda activate sllm

   sllm-serve start --host <HEAD_NODE_IP>
   # sllm-serve start --host <HEAD_NODE_IP> --port <AVAIL_PORT> # if you have changed the port
   ```
   - Replace ```your_partition``` in the script as before.
   - Replace ```/path/to/ServerlessLLM``` as before.
3. **Submit the script on the head node**

    Use ```sbatch --nodelist=idle01 start_serve.sh``` to submit the script to the head node (```idle01```).

4. **Expected output**
   ```shell
   -- Connecting to existing Ray cluster at address: xxx.xxx.xx.xx:6379...
   -- Connected to Ray cluster.
   INFO:     Started server process [1339357]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://xxx.xxx.xx.xx:8343 (Press CTRL+C to quit)
   ```
## Step 5: Use ```sllm-cli``` to manage models
1. **You can do this step on login node, and set the ```LLM_SERVER_URL``` environment variable:**
   ```shell
   $ conda activate sllm
   (sllm)$ export LLM_SERVER_URL=http://<HEAD_NODE_IP>:8343/
   ```
   - Replace ```<HEAD_NODE_IP>``` with the actual IP address of the head node.
   - Replace ```8343``` with the actual port number if you have changed it.
2. **Deploy a Model Using ```sllm-cli```**
   ```shell
   (sllm)$ sllm-cli deploy --model facebook/opt-1.3b
   ```
## Step 6: Query the Model Using OpenAI API Client
   **You can use the following command to query the model:**
   ```shell
   curl http://<HEAD_NODE_IP>:8343/v1/chat/completions \
   -H "Content-Type: application/json" \
   -d '{
         "model": "facebook/opt-1.3b",
         "messages": [
               {"role": "system", "content": "You are a helpful assistant."},
               {"role": "user", "content": "What is your name?"}
         ]
      }'
   ```
   - Replace ```<HEAD_NODE_IP>``` with the actual IP address of the head node.
   - Replace ```8343``` with the actual port number if you have changed it.