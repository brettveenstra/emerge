# Test data for C# parser validation

CSHARP_TEST_FILES = {
    "Vehicle.cs": """
/*
 * Vehicle base class and interfaces
 * Demonstrates C# classes, interfaces, and namespaces
 */

using System;
using System.Collections.Generic;

namespace Transportation.Vehicles
{
    /// <summary>
    /// Base vehicle class
    /// </summary>
    public abstract class Vehicle
    {
        public string Name { get; set; }
        public abstract void Move();

        protected int _speed;

        public Vehicle(string name)
        {
            Name = name;
        }
    }

    // Interface for flyable vehicles
    public interface IFlyable
    {
        void Fly();
        int MaxAltitude { get; }
    }

    // Interface for swimmable vehicles
    public interface ISwimmable
    {
        void Swim();
    }

    /// <summary>
    /// Generic vehicle container
    /// </summary>
    public class VehicleContainer<T> where T : Vehicle
    {
        private List<T> _vehicles = new List<T>();

        public void Add(T vehicle)
        {
            _vehicles.Add(vehicle);
        }
    }
}
""",
    "Car.cs": """
using System;
using Transportation.Vehicles;

namespace Transportation.Land
{
    /// <summary>
    /// Car class with inheritance
    /// </summary>
    public class Car : Vehicle
    {
        public int WheelCount { get; set; }

        public Car(string name) : base(name)
        {
            WheelCount = 4;
        }

        public override void Move()
        {
            Console.WriteLine("Driving");
        }

        // Nested engine class
        public class Engine
        {
            public int Horsepower { get; set; }
            public string Type { get; set; }

            public void Start()
            {
                Console.WriteLine("Engine started");
            }
        }
    }

    /// <summary>
    /// Electric car with multiple inheritance (base class + interface)
    /// </summary>
    public class ElectricCar : Car, IChargeable
    {
        public int BatteryCapacity { get; set; }

        public ElectricCar(string name) : base(name)
        {
            BatteryCapacity = 100;
        }

        public void Charge()
        {
            Console.WriteLine("Charging battery");
        }
    }

    /// <summary>
    /// Fuel type enumeration
    /// </summary>
    public enum FuelType
    {
        Petrol,
        Diesel,
        Electric,
        Hybrid
    }

    /// <summary>
    /// Position structure
    /// </summary>
    public struct Position
    {
        public double Latitude;
        public double Longitude;

        public Position(double lat, double lon)
        {
            Latitude = lat;
            Longitude = lon;
        }
    }

    /// <summary>
    /// Vehicle info record (C# 9+)
    /// </summary>
    public record VehicleInfo(string Make, string Model, int Year);

    /// <summary>
    /// Chargeable interface
    /// </summary>
    public interface IChargeable
    {
        void Charge();
        int BatteryCapacity { get; set; }
    }
}
""",
    "Airplane.cs": """
using System;
using Transportation.Vehicles;

// File-scoped namespace (C# 10+)
namespace Transportation.Air;

/// <summary>
/// Airplane with multiple interface implementations
/// </summary>
public class Airplane : Vehicle, IFlyable
{
    public int MaxAltitude { get; private set; }

    public Airplane(string name, int maxAltitude) : base(name)
    {
        MaxAltitude = maxAltitude;
    }

    public override void Move()
    {
        Fly();
    }

    public void Fly()
    {
        Console.WriteLine($"Flying at altitude {MaxAltitude}");
    }
}

/// <summary>
/// Seaplane implements both flying and swimming
/// </summary>
public class Seaplane : Airplane, ISwimmable
{
    public Seaplane(string name, int maxAltitude) : base(name, maxAltitude)
    {
    }

    public void Swim()
    {
        Console.WriteLine("Swimming on water");
    }
}
"""
}
