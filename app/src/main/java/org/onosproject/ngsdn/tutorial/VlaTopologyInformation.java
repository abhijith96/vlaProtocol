package org.onosproject.ngsdn.tutorial;

import org.onosproject.net.DeviceId;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;


public class VlaTopologyInformation {
    ArrayList<DeviceId> deviceList;
    ArrayList<DeviceId> rootDeviceList;

   HashMap<DeviceId, Integer> deviceChildIdentifierCounter;

   HashMap<DeviceId, ArrayList<DeviceId>> deviceNeighbours;

   HashMap<DeviceId, Boolean> IsConnectedToRoot;

   HashMap<DeviceId, HashMap<DeviceId, Integer>> childrenMap;

   HashMap<DeviceId,  DeviceId> parentMap;
   HashMap<DeviceId, Integer> levelMap;

   HashMap<DeviceId, Integer> deviceIdentifierMap;

    private static final Logger log = LoggerFactory.getLogger(VlaTopologyInformation.class);

    public class DeviceInfo{

        private DeviceId deviceId;

        private DeviceId parentId;
        private Integer level;

        private  Integer levelIdentifier;

        byte[] deviceAddress;

        public DeviceInfo(DeviceId deviceId, DeviceId parentId, Integer level){
            this.deviceId = deviceId;
            this.parentId = parentId;
            this.level = level;
            this.levelIdentifier = 0;
        }

        public DeviceId getDeviceId() {
            return deviceId;
        }



        public Integer GetLevel(){
            return level;
        }

        public DeviceId GetParentId() {
            return parentId;
        }

        public void SetLevelIdentifier(int levelIdentifier){
            this.levelIdentifier = levelIdentifier;
        }

        public void SetDeviceAddress(byte[] deviceAddress){
            this.deviceAddress = deviceAddress;
        }

        public int GetLevelIdentifier(){
            return levelIdentifier;
        }

        public byte[] GetDeviceAddress(){
            return deviceAddress;
        }
    };

    public class RootDeviceInfo{
        private DeviceId rootDeviceId;
       private  int level;
       private int levelIdentifier;

       private byte[] deviceAddress;

        public RootDeviceInfo(DeviceId rootDeviceId, int levelIdentifier){
            this.rootDeviceId = rootDeviceId;
            this.level = 1;
            this.levelIdentifier = levelIdentifier;
        }

        public DeviceId GetRootDeviceId(){
            return rootDeviceId;
        }

        public int GetLevel(){
            return level;
        }
        public int GetLevelIdentifier(){
            return levelIdentifier;
        }

        void SetVlaAddress(byte[] vlaAddress){
            deviceAddress = vlaAddress;
        }

        public byte[] GetVlaAddress(){
            return deviceAddress;
        }


    }


   public VlaTopologyInformation(){
       deviceList = new ArrayList<>();
       rootDeviceList = new ArrayList<>();
       deviceChildIdentifierCounter = new HashMap<>();
       deviceNeighbours = new HashMap<>();
       childrenMap = new HashMap<>();
       parentMap = new HashMap<>();
       levelMap = new HashMap<>();
       IsConnectedToRoot = new HashMap<>();
       deviceIdentifierMap = new HashMap<>();
   }

   private Integer GetIdentifier(DeviceId deviceId){
       if(deviceIdentifierMap.containsKey(deviceId)){
           return deviceIdentifierMap.get(deviceId);
       }
       return -1;
   }

   private int AddChild(DeviceId parent, DeviceId child){
       int identifier = deviceChildIdentifierCounter.get(parent);
       deviceChildIdentifierCounter.put(parent, identifier + 1);
       if(!childrenMap.containsKey(parent)){
           childrenMap.put(parent, new HashMap<>());
       }
       childrenMap.get(parent).put(child, identifier);
       return identifier;
   }

    private byte [] ConvertIntegerArrayToByteArray(int [] VlaAddressInIntegers){


        byte[] byteNumbers = new byte[2* VlaAddressInIntegers.length];

        int bitShift = AppConstants.VLA_LEVEL_BITS/ 2;

        for (int i = 0; i < VlaAddressInIntegers.length; i++) {
            int currentNum = VlaAddressInIntegers[i];
            byte second_part = (byte) currentNum;
            int tempNum = (currentNum >> bitShift);
            byte first_part = (byte) tempNum;
            byteNumbers[2*i] = first_part;
            byteNumbers[(2*i) + 1] = second_part;
        }

        return byteNumbers;
    }



  private byte [] GetVlaAddress(DeviceId deviceId, int deviceLevel){
       int [] vlaAddress = new int [AppConstants.VLA_MAX_LEVELS];
      log.info("Finding Levels up the tree. {}", deviceId);
       int currentLevel = deviceLevel;
       DeviceId currentDevice = deviceId;
       while(currentLevel > 0){
           vlaAddress [currentLevel] = deviceIdentifierMap.get(currentDevice);
           --currentLevel;
           currentDevice = parentMap.getOrDefault(currentDevice, null);
           log.info("Finding levels current device {}, current Level {} ", currentDevice, currentLevel);
           if(currentLevel == 1){
               break;
           }
       }

       return ConvertIntegerArrayToByteArray(vlaAddress);

   }

   private ArrayList<DeviceInfo> DoTraversal(DeviceId parent, DeviceId firstChild, Integer parentLevel){
       Queue<DeviceInfo> queue = new LinkedList<>();
       queue.add(new DeviceInfo(firstChild, parent, parentLevel + 1));

       ArrayList<DeviceInfo> results = new ArrayList<>();

       HashSet<DeviceId> visited = new HashSet<>();
       visited.add(parent);

       while(!queue.isEmpty()){
           DeviceInfo deviceInfo = queue.peek();
           DeviceId currentDevice = deviceInfo.deviceId;
           visited.add(currentDevice);
           parentMap.put(currentDevice, deviceInfo.GetParentId());
           levelMap.put(currentDevice, deviceInfo.GetLevel());
           int identifier = AddChild(deviceInfo.GetParentId(), currentDevice);
           deviceIdentifierMap.put(currentDevice, identifier);
           IsConnectedToRoot.put(currentDevice, true);
           deviceInfo.SetLevelIdentifier(identifier);
           deviceInfo.SetDeviceAddress(GetVlaAddress(currentDevice, deviceInfo.GetLevel()));
           results.add(deviceInfo);
           queue.poll();

           for(DeviceId deviceId : deviceNeighbours.get(currentDevice)){
               if(deviceNeighbours.get(deviceId).contains(currentDevice)){
                  if(!visited.contains(deviceId)){
                      queue.add(new DeviceInfo(deviceId, currentDevice, deviceInfo.GetLevel() + 1));
                  }
               }
           }
       }
       return results;
   }


   private ArrayList<DeviceInfo> UpdateLevels(DeviceId source, DeviceId dest){

        log.info("In Update Levels part source device {},  destination device {}", source, dest);
       if(IsValidLinkToAdd(source, dest)){
           DeviceId originalSource = source;
           DeviceId originalDestination = dest;
           if(IsConnectedToRoot.get(dest)){
               originalSource = dest;
               originalDestination = source;
           }
           int parentLevel = 1;
           if(!rootDeviceList.contains(originalSource)){
               parentLevel = levelMap.get(originalSource);
           }
          return DoTraversal(originalSource, originalDestination, parentLevel);
       }
       return new ArrayList<>();
   }

   private boolean IsValidLinkToAdd(DeviceId source, DeviceId destination){

           if (deviceNeighbours.get(source).contains(destination) &&
                   deviceNeighbours.get(destination).contains(source)) {
               if (IsConnectedToRoot.get(source) && IsConnectedToRoot.get(destination)) {
                   return false;
               }
               return IsConnectedToRoot.get(source) || IsConnectedToRoot.get(destination);
           }

       return false;
   }

    public Optional<RootDeviceInfo> AddDevice(DeviceId deviceId, boolean IsRootDevice){
        synchronized (this) {
            if(!deviceList.contains(deviceId)) {
                deviceList.add(deviceId);
                deviceNeighbours.put(deviceId, new ArrayList<>());
                deviceChildIdentifierCounter.put(deviceId, 1);
                IsConnectedToRoot.put(deviceId, false);
            }
            if(IsRootDevice && !rootDeviceList.contains(deviceId)){
                int len = rootDeviceList.size();
                rootDeviceList.add(deviceId);
                IsConnectedToRoot.put(deviceId, true);
                deviceChildIdentifierCounter.put(deviceId, len + 1);
                levelMap.put(deviceId, 1);
                int levelIdentifier = rootDeviceList.indexOf(deviceId);
                deviceIdentifierMap.put(deviceId, levelIdentifier);
                RootDeviceInfo rootDeviceInfo = new RootDeviceInfo(deviceId, levelIdentifier);
                rootDeviceInfo.SetVlaAddress(GetVlaAddress(deviceId, 1));
                return Optional.of(rootDeviceInfo);
            }
        }
        return Optional.empty();
    }

    public void RemoveDevice(DeviceId deviceId){
        synchronized (this) {
            if(deviceList.contains(deviceId)) {
                deviceList.remove(deviceId);
                // TODO
                //remove flow table entries related to device.
            }
        }
    }

    public ArrayList<DeviceInfo> AddLink(DeviceId source, DeviceId destination){
        synchronized (this){
            deviceNeighbours.get(source).add(destination);
            deviceNeighbours.get(destination).add(source);
            if(IsValidLinkToAdd(source, destination)){
               return UpdateLevels(source, destination);
            }
        }
        return new ArrayList<DeviceInfo>();
    }
}