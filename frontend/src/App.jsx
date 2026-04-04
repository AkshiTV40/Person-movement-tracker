              {mode !== 'youtube' && mode !== 'instructions' && (
                <motion.div 
                  className="flex items-center space-x-3"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className={`w-3 h-3 rounded-full ${isActive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
                  <span className="text-sm font-medium text-gray-700">
                    {isActive ? 'Camera Active' : 'Camera Inactive'}
                  </span>
                </motion.div>
              )}